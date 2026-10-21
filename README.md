# なろうVTuberになろう サンプルコード

技術書「なろうVTuberになろう！」のLinux用セットアップ、RVC音声モデル制作、Blenderアバター制作に使うサンプルコードです。原稿中のコマンドと同じパスで実行できるように、`examples/chukei/` 以下の構成を保っています。

## サンプルの取得

Gitを使う場合は、次のコマンドで取得します。

```bash
git clone https://github.com/tyukei/narou-vtuber-samples.git
cd narou-vtuber-samples
```

Gitを使わない場合は、このページの **Code → Download ZIP** から取得して展開します。展開した `narou-vtuber-samples-main` フォルダーが、原稿に出てくる「サンプルコードのルート」です。以降のコマンドは、このフォルダーを作業場所にして実行してください。

基本編のMac・Windowsでの手動設定には、このリポジトリを取得する必要はありません。Linuxの一括準備や応用編に進むときに使います。

## 収録内容

| ディレクトリ | 対応する内容 | 必要な環境 | 詳細 |
| --- | --- | --- | --- |
| `examples/chukei/setup/` | LinuxでVC Client・OBS・仮想音声を準備する | Linux x86_64、Docker、Flatpak、PulseAudio互換環境 | [Linuxセットアップ](examples/chukei/setup/README.md) |
| `examples/chukei/voice-model/` | 歴史上の本人録音からRVCモデルを追加学習する | Linux、Python 3.12、NVIDIA GPU、FFmpeg、uv | [音声モデル制作](examples/chukei/voice-model/README.txt) |
| `examples/chukei/avatar/` | Blenderでマスコットを作りVRMを書き出す | Blender、Blender MCP、VRM Add-on for Blender | [アバター制作](examples/chukei/avatar/README.txt) |

各サンプルのREADMEに、導入手順、実行順序、確認済みの環境と未検証の範囲を記載しています。LinuxセットアップはCPUでの検証で、GPU利用は追加の環境設定が必要です。

## まず実行予定だけを確認する

Linuxのセットアップスクリプトは、変更内容を事前に確認できます。

```bash
bash examples/chukei/setup/vtuber.sh setup --dry-run
```

導入と起動は、LinuxセットアップのREADMEに従って進めます。起動コマンドと停止コマンドは、使うタイミングを分けて実行してください。

## 出力先

音声モデルの作業環境と取得したデータは `.locals/voice-model/`、学習結果は `output/voice-model/` に保存します。アバターの出力先は `output/avatar/` です。Linuxセットアップの既定の保存先は `~/.local/share/isekai-vtuber` です。ダウンロード済みのモデル、録音、生成したVRMやBlenderファイルは、このリポジトリには含めていません。

アバター制作では制作専用の空のシーンを使います。`build_avatar.py` はシーン内のオブジェクトを削除して制作を始めるため、編集中のシーンでは実行しないでください。元絵・三面図の画像は含めていませんが、配布Pythonにモデルの形状と材質の定義があります。

## 素材と外部ソフトウェア

音声素材の出典・取得URL・ハッシュは [sources.json](examples/chukei/voice-model/sources.json)、採用根拠は [RIGHTS.txt](examples/chukei/voice-model/RIGHTS.txt) にあります。別の素材へ差し替える場合は、その素材の利用条件を確認してください。

VC Client、OBS、Blender、VRM用アドオン、RVCのプログラムと事前学習済みモデルは、それぞれの配布元から取得します。各ソフトウェア・モデルのライセンスと利用条件は、配布元の案内に従ってください。

- [VC Client](https://github.com/w-okada/voice-changer)
- [OBS Studio](https://obsproject.com/)
- [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
- [Blender](https://www.blender.org/)
- [Blender MCP](https://github.com/ahujasid/mcp-for-blender)
- [VRM Add-on for Blender](https://vrm-addon-for-blender.info/ja-jp/)

## 変更を加えずに実行できる確認

```bash
bash -n examples/chukei/setup/vtuber.sh
python3 examples/chukei/setup/verify_setup.py
```

`verify_setup.py` の通常実行は引数の検査とdry-runの確認です。Docker・OBSを起動する検証は `--integration` を付けた場合だけ実行します。保存済みの `validation.json` は執筆時の記録です。
