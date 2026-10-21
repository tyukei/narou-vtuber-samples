画像からVRMを作る実験（2026-10-04）

対応章: 「なろうVTuberになろう！」応用編第二章
成果物: output/avatar/pineapple-avatar.blend, pineapple-avatar.vrm
実画像: images/chukei/avatar/

追試の前提
- Blender 4.5.14、MCP for Blender 2.1.3のBlender側アドオン
- VRM Add-on for Blender 4.7.2を有効化
- Pythonのmcpパッケージとuvx（MCPクライアントをCLIで使う場合）
- 制作用の空のシーン。build_avatar.pyはシーン内の物体を削除する。

Codexに元絵と三面図を渡し、原稿のプロンプトを順に実行する。
コードで追試する場合は、MCP execute_blender_codeへ次の順で送る。

1. bpy.context.scene['avatar_project_root'] = リポジトリの絶対パス
2. build_avatar.pyの全文
3. rig_export.pyの全文
4. check_roundtrip.pyの全文

mcp_call.pyの呼び出し:
uv run --with mcp python examples/chukei/avatar/mcp_call.py \
  execute_blender_code request.json response.json

request.jsonは {"code": "実行するPython", "user_prompt": "依頼文"}。
get_viewport_screenshotなら {"max_size":1600,"user_prompt":"依頼文"}。
画像はresponse.jsonと同じ場所へ.pngとして保存される。
BLENDER_PORT環境変数を省略すると既定の9876。実験では9877を使用。
AVATAR_MCP_SERVERを指定するとインストール済みサーバー実行ファイルを使う。
このラッパーはMCPサーバーの追加テレメトリを無効にする。

start_blender.pyは別のBlenderを起動するための補助。
AVATAR_VRM_ADDONにVRMアドオンのパッケージディレクトリ、
AVATAR_MCP_ADDONにblender_mcp.pyのあるディレクトリを指定する。
blender --factory-startup --python examples/chukei/avatar/start_blender.py
これは制作専用のプロセスで実行し、作業中のBlenderには実行しない。

再現コードでは肩の修正を反映済み。fix_shoulders.pyは実験履歴用。
check_roundtrip.pyは新しいシーンへVRMを読み込み、テストポーズを付ける。
納品用ファイルはTポーズのまま。追試は同名の成果物を上書きするため、
自分で変更したモデルを残す場合は出力先を変える。

既知の範囲:
胴体は腰に固定、手足は部品ごとの単一ボーンウェイト。
指、視線追従、揺れ物、実体のある口腔は未実装。
blinkは目を縦につぶし、aaは笑顔の線を伸ばす簡易表情。
VRM 1.0版の外部トラッキング動作は未確認。VRM 0.x版の追試は下記。
VRMメタデータの作者名・利用条件は仮設定。配布前に編集する。

Kalidoface向け追試:
export_kalidoface.pyは元のPineappleRigシーンを使い、VRM 0.xの別版を生成。
output/avatar/pineapple-kalidoface.vrmと同名.blendが成果物。
まばたき・左右のウインク・A/I/U/E/Oを設定。視線追従は未実装。
check_kalidoface_blender.pyは再読み込みして表情の頂点差分を検査する。
check_kalidoface_runtime.mjsはthree-vrmの実ローダーと表情の重みを検証。
実行準備:
npm install --prefix output/avatar/kalido-runtime --legacy-peer-deps \
  --no-audit --no-fund three@0.138.3 @pixiv/three-vrm@0.6.10
node examples/chukei/avatar/check_kalidoface_runtime.mjs
これは公開アプリの依存バージョンを再現するためpeer依存の差を許容する。
ブラウザー/WebGL/カメラは使わない単体検証。Kalidoface本体の実証とは別。
2026-10-05: ChromeのKalidofaceにVRM 0.x版を投入し、640x480のカメラ映像と
追跡点、姿勢変化を確認。利用者からモーションと母音の動作報告あり。
水面背景では靴・すねに連動した浮遊物が出たが、Backgrounds > Whiteで解消。
モデルの部品削除は不要。五母音それぞれの判定精度までは未検証。
