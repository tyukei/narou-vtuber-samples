#!/usr/bin/env bash
# Linux x86_64 reference environment. See README.md for versions and manual steps.
set -euo pipefail
umask 077

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
IMAGE='dannadori/vcclient@sha256:01ae74a73d2c312a839be77ee9b8ad6c7fc688f7e26f943301a00c531c01ff41'
APP=com.obsproject.Studio
WORK_DIR=${VTUBER_HOME:-"${XDG_DATA_HOME:-$HOME/.local/share}/isekai-vtuber"}
PORT=18888
TIMEOUT=1200
OPEN=1
GPU=0
SERVER_ONLY=0
DRY_RUN=0
COMMAND=${1:-help}
if (($#)); then shift; fi

usage() {
    cat <<'EOF'
使い方: bash vtuber.sh setup|start|status|stop [オプション]
  --dir PATH       保存先（既定: ~/.local/share/isekai-vtuber）
  --port NUMBER    VC Clientのポート（既定: 18888、localhostのみ）
  --timeout SEC    初回ダウンロードの待ち時間（既定: 1200秒）
  --gpu            NVIDIA Container Toolkit設定済みのGPUを使う
  --no-open        ブラウザを開かない
  --server-only    OBSを起動せず、VC Clientと音声デバイスを準備
  --dry-run        実行予定を表示するだけ
  --help           この説明を表示
setup: OBSとVC Clientを取得し、独立したOBS設定を用意
start: 仮想音声デバイス、VC Client、OBS、ブラウザを起動
status: サーバーと音声デバイスの状態を表示
stop: このスクリプトで起動したものを停止（保存済みデータは保持）
Linux x86_64、Docker、Flatpak、curl、pactl、flockが必要です。
EOF
}

fail() { printf 'エラー: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 が見つかりません。READMEの前提を確認しましょう。"; }
while (($#)); do
    case $1 in
        --dir|--port|--timeout)
            (($# >= 2)) || fail "$1 の値が必要です。"
            case $1 in --dir) WORK_DIR=$2;; --port) PORT=$2;; --timeout) TIMEOUT=$2;; esac
            shift 2;;
        --gpu) GPU=1; shift;;
        --no-open) OPEN=0; shift;;
        --server-only) SERVER_ONLY=1; shift;;
        --dry-run) DRY_RUN=1; shift;;
        --help) usage; exit 0;;
        *) fail "不明なオプション: $1";;
    esac
done
case $COMMAND in setup|start|status|stop) ;; help|--help|-h) usage; exit 0;; *) fail "不明な操作: $COMMAND";; esac
if ! [[ $PORT =~ ^[0-9]{1,5}$ ]] || ((10#$PORT < 1024 || 10#$PORT > 65535)); then
    fail 'portは1024〜65535で指定しましょう。'
fi
PORT=$((10#$PORT))
if ! [[ $TIMEOUT =~ ^[0-9]{1,5}$ ]] || ((10#$TIMEOUT == 0)); then
    fail 'timeoutは正の秒数で指定しましょう。'
fi
TIMEOUT=$((10#$TIMEOUT))
[[ -n $WORK_DIR && $WORK_DIR != / && $WORK_DIR != *$'\n'* && $WORK_DIR != *:* ]] || fail '保存先の指定を確認しましょう。'
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || fail 'この補助スクリプトはLinux x86_64用です。Macは本文の手順を使いましょう。'
need realpath
WORK_DIR=$(realpath -m -- "$WORK_DIR")
NAME="isekai-vtuber-$(printf '%s' "$WORK_DIR" | cksum | cut -d ' ' -f 1)"
SINK="vtuber_bus_${NAME##*-}"
URL="http://localhost:$PORT/"
if ((DRY_RUN)); then
    printf '操作: %s\n保存先: %s\nVC Client: %s\nDocker: %s\n音声: %s（入力は.monitor）\nOBS: %s\n' "$COMMAND" "$WORK_DIR" "$URL" "$IMAGE" "$SINK" "$APP"
    exit 0
fi
need docker
need flock
docker info >/dev/null 2>&1 || fail 'Dockerを起動し、実行権限を確認しましょう。'
mkdir -p -- "$WORK_DIR"
exec 9>"$WORK_DIR/.lock"
flock -n 9 || fail '同じ保存先で別の操作が実行中です。'

owned_container() {
    [[ $(docker inspect --format '{{index .Config.Labels "jp.isekai.workdir"}}' "$NAME" 2>/dev/null || true) == "$WORK_DIR" ]]
}
container_exists() { docker inspect "$NAME" >/dev/null 2>&1; }
sink_exists() { pactl list short sinks | awk -v name="$SINK" '$2==name {found=1} END {exit !found}'; }
obs_owned() {
    [[ -f $WORK_DIR/obs.pid ]] || return 1
    local pid
    read -r pid <"$WORK_DIR/obs.pid"
    [[ $pid =~ ^[0-9]+$ && -r /proc/$pid/environ ]] || return 1
    tr '\0' '\n' <"/proc/$pid/environ" | grep -Fx "VTUBER_WORK_DIR=$WORK_DIR" >/dev/null
}
health() { curl --fail --silent --max-time 3 "$URL" >/dev/null; }

case $COMMAND in
    setup)
        need flatpak
        need curl
        # Allow an offline rerun once packages exist. Installing Docker itself
        # remains an explicit OS administrator task.
        if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
            free_kb=$(df -Pk -- "$WORK_DIR" | awk 'NR==2 {print $4}')
            minimum_kb=$((24*1024*1024))
            if flatpak info --user "$APP" >/dev/null 2>&1; then minimum_kb=$((20*1024*1024)); fi
            ((free_kb >= minimum_kb)) || fail '取得・展開の空き容量が不足しています。32GiB以上を目安にし、Dockerの保存先も確認しましょう。'
            docker pull "$IMAGE"
        fi
        if ! flatpak info --user "$APP" >/dev/null 2>&1; then
            flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
            flatpak install --user --noninteractive -y flathub "$APP"
        fi
        mkdir -p -- "$WORK_DIR/pretrain" "$WORK_DIR/model_dir" "$WORK_DIR/obs-config/obs-studio"
        # Copy only missing files; subsequent setup keeps adjustments intact.
        while IFS= read -r -d '' source; do
            relative=${source#"$SCRIPT_DIR/obs-studio/"}
            destination="$WORK_DIR/obs-config/obs-studio/$relative"
            mkdir -p -- "$(dirname -- "$destination")"
            if [[ ! -e $destination && ! -L $destination ]]; then
                cp -- "$source" "$destination"
            fi
        done < <(find "$SCRIPT_DIR/obs-studio" -type f -print0)
        printf '準備できました。次は start で起動していきましょう。\n'
        ;;
    start)
        need curl
        need pactl
        [[ -d $WORK_DIR/model_dir && -d $WORK_DIR/obs-config/obs-studio ]] || fail '最初にsetupを実行しましょう。'
        docker image inspect "$IMAGE" >/dev/null 2>&1 || fail 'VC Clientが未取得です。setupを実行しましょう。'
        if ((OPEN)); then need xdg-open; need nohup; need setsid; fi
        if ((!SERVER_ONLY)); then
            need flatpak
            need pgrep
            need nohup
            need setsid
            flatpak info --user "$APP" >/dev/null 2>&1 || fail 'OBSが未導入です。setupを実行しましょう。'
        fi
        pactl info >/dev/null 2>&1 || fail 'PulseAudioまたはPipeWireの音声セッションを確認しましょう。'
        if container_exists; then
            owned_container || fail '同名の別コンテナがあります。停止せず終了します。'
            [[ $(docker inspect --format '{{.State.Running}}' "$NAME") == true ]] || fail '既存コンテナが停止しています。stopを実行してから再起動しましょう。'
            [[ $(docker port "$NAME" 18888/tcp) == "127.0.0.1:$PORT" ]] || fail '起動済みのポートと指定が違います。stopしてから起動しましょう。'
        else
            options=()
            if ((GPU)); then options+=(--gpus all); fi
            # HTTP localhost is a browser secure context for microphone access.
            # The published port remains on loopback; no physical audio devices
            # or camera devices are passed into the container.
            docker run -d --name "$NAME" --label "jp.isekai.workdir=$WORK_DIR" \
                --shm-size 1024m "${options[@]}" \
                -e "LOCAL_UID=$(id -u)" -e "LOCAL_GID=$(id -g)" \
                -e EX_IP=127.0.0.1 -e "EX_PORT=$PORT" \
                -v "$WORK_DIR/pretrain:/voice-changer/server/pretrain" \
                -v "$WORK_DIR/model_dir:/voice-changer/server/model_dir" \
                -p "127.0.0.1:$PORT:18888" "$IMAGE" -p 18888 --https false >/dev/null
        fi
        if ! sink_exists; then
            pactl load-module module-null-sink "sink_name=$SINK" \
                sink_properties=device.description=VTuberBus >"$WORK_DIR/audio.module"
        fi
        printf 'VC Clientの準備を待っています（初回はモデル取得があります）。\n'
        ready=0
        for ((elapsed=0; elapsed<TIMEOUT; elapsed+=2)); do
            if health; then ready=1; break; fi
            [[ $(docker inspect --format '{{.State.Running}}' "$NAME") == true ]] || {
                docker logs --tail 25 "$NAME" >&2
                fail 'VC Clientが終了しました。ログを確認し、stopで片付けてから再試行しましょう。'
            }
            sleep 2
        done
        ((ready)) || fail "起動待ちが時間切れです。docker logs $NAME で確認できます。stopで停止できます。"
        for weight in content_vec_500.onnx hubert_base.pt rmvpe.pt; do
            if [[ ! -f $WORK_DIR/pretrain/$weight ]] || \
                (( $(stat -c %s -- "$WORK_DIR/pretrain/$weight") <= 1000000 )); then
                fail "RVC共通モデル $weight の取得を確認できません。docker logs $NAME を確認しましょう。"
            fi
        done
        if [[ -f $WORK_DIR/pretrain/rinna_hubert_base_jp.pt ]] && \
            (( $(stat -c %s -- "$WORK_DIR/pretrain/rinna_hubert_base_jp.pt") < 1000000 )); then
            printf '補足: 日本語HuBERTの重みは未取得です。日本語HuBERTへの切替には別途取得が必要です（README参照）。\n'
        fi
        if ((!SERVER_ONLY)) && ! obs_owned; then
            # Flatpak resets XDG_CONFIG_HOME, so env runs inside its sandbox.
            # Record the actual OBS PID, rather than the outer bwrap PID.
            nohup setsid flatpak run --filesystem="$WORK_DIR/obs-config" \
                --command=env "$APP" "XDG_CONFIG_HOME=$WORK_DIR/obs-config" \
                "VTUBER_WORK_DIR=$WORK_DIR" obs --multi --profile Isekai --collection Isekai \
                >"$WORK_DIR/obs.log" 2>&1 </dev/null 9>&- &
            for ((attempt=0; attempt<20; attempt++)); do
                while read -r candidate; do
                    if [[ -r /proc/$candidate/environ ]] && \
                        tr '\0' '\n' <"/proc/$candidate/environ" | grep -Fx "VTUBER_WORK_DIR=$WORK_DIR" >/dev/null; then
                        printf '%s\n' "$candidate" >"$WORK_DIR/obs.pid"
                        break
                    fi
                done < <(pgrep -x obs || true)
                if obs_owned; then break; fi
                sleep 1
            done
            obs_owned || fail "OBSを起動できませんでした。$WORK_DIR/obs.log を確認しましょう。"
        fi
        if ((OPEN)); then
            nohup setsid xdg-open "$URL" >/dev/null 2>&1 9>&- &
            nohup setsid xdg-open https://3d.kalidoface.com/ >/dev/null 2>&1 9>&- &
        fi
        printf '起動しました: %s\nVC ClientのClient Audioで、OutはVTuberBus、Monはイヤホンを選びましょう。\n会議アプリのマイクは %s.monitor です。\n' "$URL" "$SINK"
        ;;
    status)
        need curl
        need pactl
        if owned_container; then
            live_port=$(docker port "$NAME" 18888/tcp)
            URL="http://localhost:${live_port##*:}/"
        fi
        if owned_container && health; then printf 'VC Client: 起動中 %s\n' "$URL"; else printf 'VC Client: 停止／準備中\n'; fi
        if sink_exists; then printf '仮想音声: %s / %s.monitor\n' "$SINK" "$SINK"; else printf '仮想音声: 未作成\n'; fi
        if obs_owned; then printf 'OBS: 起動中\n'; else printf 'OBS: 停止\n'; fi
        ;;
    stop)
        if container_exists; then
            owned_container || fail '同名コンテナが別の保存先に属するため、停止しません。'
            docker rm -f "$NAME" >/dev/null
        fi
        if [[ -f $WORK_DIR/audio.module ]]; then
            need pactl
            read -r module <"$WORK_DIR/audio.module"
            # Module ids may be reused after an audio-server restart.
            if [[ $module =~ ^[0-9]+$ ]] && pactl list short modules | awk -v id="$module" -v name="$SINK" \
                '$1==id && $2=="module-null-sink" {for(i=3;i<=NF;i++) if($i=="sink_name="name) found=1} END {exit !found}'; then
                pactl unload-module "$module"
            fi
            rm -f -- "$WORK_DIR/audio.module"
        fi
        if obs_owned; then
            read -r pid <"$WORK_DIR/obs.pid"
            kill -- "$pid"
        fi
        rm -f -- "$WORK_DIR/obs.pid"
        printf '停止しました。モデルとOBS設定は保存しています。ブラウザのタブは手で閉じていきましょう。\n'
        ;;
esac
