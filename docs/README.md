# 自分だけの声と姿を作る

音声モデルとアバターを、仕組みから制作・確認まで同じ流れで試せます。

| | 声を作る | 姿を作る |
|---|---|---|
| 技術 | RVC v2の追加学習と特徴検索 | 画像生成、Blenderの形状・骨・表情、VRM |
| 制作手順 | [音声モデル](voice.md) | [アバター](avatar.md) |
| 完成品を試す | voice-model-v1.zipの.pthと.index | avatar-v1.zipのpineapple-kalidoface.vrm |
| 確認 | 新しい発話の変換、入力との聴き比べ | 再読み込み、骨・表情、利用アプリでの動作 |

## 完成品を入手する

[応用編の配布ページ advanced-v1](https://github.com/tyukei/narou-vtuber-samples/releases/tag/advanced-v1) の **Assets** から必要なZIPをダウンロードします。GitHubが自動表示するSource codeのZIPには、モデル本体は入りません。

ZIPをサンプルコードのルートへ展開すると、`output/voice-model/` または `output/avatar/` ができます。展開済みの自分の成果物を上書きしないよう、初めて試すときは新しく取得した作業コピーを使ってください。各ZIPにREADME、利用条件、検証結果、SHA256SUMSが入っています。

[SHA256SUMS](https://github.com/tyukei/narou-vtuber-samples/releases/download/advanced-v1/SHA256SUMS) はダウンロードしたZIPの確認用です。Linuxでは `sha256sum -c SHA256SUMS`、macOSでは `shasum -a 256 -c SHA256SUMS` を使います。Windowsでは `Get-FileHash .\voice-model-v1.zip -Algorithm SHA256` の値を照合します。片方だけ取得した場合は、そのファイルの行だけ照合してください。

## 再現する版を固定する

```bash
git clone https://github.com/tyukei/narou-vtuber-samples.git
cd narou-vtuber-samples
git checkout advanced-v1
```

公開されているのは教材用のサンプルです。音声は機械生成であり、歴史上の本人の実際の発言ではありません。アバターは[利用条件](../examples/chukei/avatar/USAGE.txt)に従って個人の非営利目的で試せます。確認済みの範囲と未検証の範囲は各ガイドに分けて記載しています。
