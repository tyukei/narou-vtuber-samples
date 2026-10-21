# Linuxで準備と起動をまとめる

本編の手操作を、Linuxの参考構成ではBashでまとめられます。実行するのは
`vtuber.sh`です。VRoid Studioでの制作とブラウザ・会議アプリのデバイス選択は
手で進めていきましょう。

## 前提

- Linux x86_64のデスクトップ。Ubuntu 24.04で検証しました。
- Dockerの起動と利用権限、Flatpak、curl、flock（util-linux）、pactl
  （pulseaudio-utils）、標準のGNUコマンドが必要です。ブラウザを開く場合は
  xdg-openも使います。
- 音声はPulseAudio、またはPulseAudio互換機能のあるPipeWireを使います。
- 初回は32GiB以上の空き容量を目安にしましょう。Dockerの保存先にも空きが
  必要です。VC Clientの配布イメージは約8.1GBで、Dockerの取得・展開キャッシュにも空きが必要です。
  OBSとそのランタイムが約3.3GB、初回の共通モデルが約1.6GBでした。
- インターネット接続とChrome系ブラウザを用意しておきましょう。

未導入のコマンドはOSのパッケージ管理で用意します。Ubuntuでは例えば
`sudo apt install docker.io flatpak curl pulseaudio-utils util-linux xdg-utils`
です。Dockerの利用権限やサービス起動は、そのPCの管理方針に合わせて設定して
いきましょう。スクリプトはsudo、グループ変更、OSの権限変更を実行しません。

## 初回の取得と設定

リポジトリのルートから実行します。

```bash
bash examples/chukei/setup/vtuber.sh setup --dry-run
bash examples/chukei/setup/vtuber.sh setup
```

`setup`でVC ClientのDockerイメージと、ユーザー用のOBS Flatpakを取得します。
OBSは1280×720、30fps、48kHzの初期設定と、空の`Avatar`シーンを用意します。
保存先は`~/.local/share/isekai-vtuber`です。`--dir "$HOME/VTuber files"`で変えられます。
再実行では既存のダウンロードと設定を使い、作成済みの設定ファイルを上書きしません。
OBS自体も導入済みなら再インストールしません。

## 毎回の起動

```bash
bash examples/chukei/setup/vtuber.sh start
bash examples/chukei/setup/vtuber.sh status
```

起動時には次の準備を行います。

1. VC ClientをDockerで起動。公開ポートは`127.0.0.1:18888`に限定します。
   初回の共通モデル取得が終わるまで待ちます（最大20分）。
2. `VTuberBus`という仮想音声出力を作成。会議に渡す入力は、その`.monitor`です。
3. この保存先のOBS設定でOBSを起動します。
4. VC ClientとKalidofaceのページを既定のブラウザで開きます。

本編のMac版2.xとは異なり、Linuxでは作者の公式起動スクリプトに記載された
Docker版v.1.5.3.13を使います。RVC対応ですが、UIやサンプル一覧は異なります。
VC Clientイメージはdigestを固定しています。OBSはFlathubのstable配布を使い、
検証時は32.2.2でした。OBSのバージョンは固定していません。
VRoid StudioはLinux向け公式版がないため、このスクリプトでは導入しません。
別のWindows/Macで作ったVRMをKalidofaceへ読み込んで使えます。

VC Clientはブラウザの**Client Audio**を使います。Docker内のServer Audioは
ホストのマイクへ直接つないでいません。RVCモデルの追加と利用条件の確認を済ませ、
次の経路を画面で選んでいきましょう。

| 選ぶ場所 | 指定するもの |
| --- | --- |
| VC ClientのIn | 自分のマイク |
| VC ClientのOut | VTuberBus |
| VC ClientのMon | イヤホン／ヘッドホン |
| 会議アプリのマイク | VTuberBusのMonitor（内部名は`vtuber_bus_数字.monitor`） |
| 会議アプリのカメラ | OBS Virtual Camera |

ブラウザから音声出力を選べない場合は、OSのサウンド設定で**VC Clientを再生する
ブラウザの出力先だけ**をVTuberBusへ変更します。OS全体の出力先はそのままに
しておくと、ほかのアプリの音が入り込むのを避けやすくなります。
VC Clientと会議が同じブラウザの音声ストリームにまとまる環境では、別のブラウザや
会議アプリを使って再生先を分けていきましょう。

このDocker版は起動時に複数方式の共通モデルを取得します。検証時は日本語HuBERTの
取得先が認証必須（HTTP 401）になっていました。今回のRVCは標準の特徴抽出モデルを使います。スクリプトはRVC用の主要な重みのサイズを確認し、未取得ならエラーにします。
日本語HuBERTへ切り替える場合は、配布元の利用条件と認証付きの取得方法を別途
確認していきましょう。

KalidofaceへのVRM読み込み、カメラ・マイクの許可、OBSへのウィンドウ取り込み、
仮想カメラ開始は本文の操作で進めます。LinuxのOBS仮想カメラには
`v4l2loopback`カーネルモジュールも必要です。このスクリプトはカーネルモジュールを
導入・ロードしません。Waylandでは「画面キャプチャ（PipeWire）」の共有ダイアログ
から対象を選ぶ方法もあります。

## 停止・オプション

```bash
bash examples/chukei/setup/vtuber.sh stop
```

スクリプトのコンテナ、OBS、作成した仮想音声デバイスを停止します。モデルとOBSの
設定は残ります。VC ClientとKalidofaceのブラウザタブは手で閉じていきましょう。
音声サーバー再起動後にモジュール番号が変わった場合も、別のデバイスを消さないよう
番号とデバイス名の両方を確認します。

- `--no-open`：ブラウザを開かず起動。
- `--server-only`：OBSを起動せず、VC Clientと仮想音声だけを準備。
- `--gpu`：NVIDIA GPUとNVIDIA Container Toolkitを設定済みの場合に使用。
  既定はCPUです。GPU分岐は今回の実動作検証対象に含めていません。
- `--port 18889`：ポートの変更。起動済みのポートを変えるときは一度`stop`します。
- `--timeout 1800`：初回取得が遅い場合に待ち時間を延長。
- `--dir PATH`：保存先。毎回同じ指定で実行します。空白を含むパスは引用符で囲みます。
- `VTUBER_HOME`：`--dir`の代わりに既定の保存先を環境変数で指定できます。

起動待ちが時間切れになっても、途中取得済みのモデルは残ります。`status`と
`docker logs`で確認し、`stop`してから再試行できます。
OBSが起動しない場合は保存先の`obs.log`を確認していきましょう。
起動済みのコンテナ名が別の保存先に属する場合は、停止・置き換えを行わず終了します。
配信開始の操作は含めていません。

## 実動作の検証

構文と静的検査：

```bash
bash -n examples/chukei/setup/vtuber.sh
shellcheck examples/chukei/setup/vtuber.sh
python3 examples/chukei/setup/verify_setup.py
```

Docker・OBSを実際に起動する検証は、別の保存先で実施できます。OBSウィンドウが
開き、仮想音声へテスト音が送られます。録音するのはそのMonitorだけです。

```bash
python3 examples/chukei/setup/verify_setup.py \
  --integration --dir "$HOME/VTuber verification"
```

検証結果は`validation.json`を参照できます。公式コマンドによる初回取得と、取得済み
パッケージを使うsetup、HTTPと設定APIの応答、
OBSのプロファイル・シーン、1000Hzのテスト音の通過、再実行での設定保持、
起動の重複防止、停止と再起動、空白を含むパス、モジュール番号が別の音声デバイスに
再利用されたときの保護を確認しました。別途、付録の既存RVCモデルで保存済み音声
ファイルの変換も実行し、2秒の入力に対するPCM出力を確認しています。
Webカメラ・生マイクでのリアルタイム変換、GPU、仮想カメラ出力、Macでの実行は
未検証です。ブラウザを開く分岐は既定ブラウザの個人設定に依存するため、実動作検証では
`--no-open`を使っています。

## 参照

- [VC Client Docker公式手順](https://github.com/w-okada/voice-changer/blob/master/docker_vcclient/README.md)
- [公式start_docker.sh（配布イメージのタグ）](https://github.com/w-okada/voice-changer/blob/master/start_docker.sh)
- [OBS Linuxの導入](https://obsproject.com/kb/linux-installation)
- [OBSの起動引数](https://obsproject.com/kb/launch-parameters)
- [OBS Virtual Camera Guide](https://obsproject.com/kb/virtual-camera-guide)
