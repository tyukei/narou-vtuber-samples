応用編第一章：パブリックドメイン録音からRVCモデルを作る

人物：セオドア・ルーズベルト（第26代米国大統領、1858–1919）。
素材は本人の1912年録音2本。RIGHTS.txtとsources.jsonに出典と採用根拠を記録。
このディレクトリは再現用コードです。成果物はoutput/voice-model/にあります。

環境
Ubuntu / Python 3.12.3 / NVIDIA RTX 4070 Ti SUPER 16GB。
PyTorch 2.7.1+cu118、RVC v2、40kHz、ピッチあり、RMVPE。
Macでの学習やVC ClientのGUIへの登録は、この実験の動作確認範囲外です。
コードとモデルは下記のコミットに固定し、別の最新版へ読み替えません。
RVC: 81eed5e8f68b6bed1789f682fe78cdd324495afc
配布モデル: lj1995/VoiceConversionWebUI @ e6d0c1a17da07c33557852f9dfa2bd44cc75737d

準備（リポジトリのルートで実行）
FFmpeg、Git、curl、Python 3.12、uv、NVIDIAドライバが必要です。
専用環境の展開に数GB、チェックポイントとダウンロードキャッシュにも
容量を使います。システムPythonのパッケージを変更しません。

  uv venv --python 3.12 .locals/voice-model/venv
  uv pip install --python .locals/voice-model/venv/bin/python -r examples/chukei/voice-model/requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cu118 --index-strategy unsafe-best-match
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/run.py download

実行した工程
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/run.py prepare
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/run.py features
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/run.py train --epochs 30 --batch 6
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/run.py export

prepareは元音源のハッシュを照合してから学習区間と参照区間を切り出します。
前処理は80Hzハイパス、5.5kHzローパス、控えめなFFTノイズ抑制です。
ニューラル音声修復による作り直しは行っていません。
学習候補区間は合計355秒、参照区間は合計40秒。間に10秒の未使用区間を
置きます。同じ録音内の分割なので、独立した録音条件への汎化評価では
ありません。前処理後の実際の秒数・セグメント数はvalidation.jsonを参照。

featuresはRMVPEのピッチとHuBERT/ContentVecの768次元特徴を抽出し、
学習区間のみからFAISS検索インデックスを作ります。文字起こしは不要です。
trainは既存の生成器・識別器を追加学習します。エポックはデータ一巡、
バッチは一度に渡す区間数です。数を増やせば必ず音質が上がるわけではありません。
同じ実験名でtrainを再実行すると保存済みのチェックポイントから再開します。
独立した追試には別の作業コピーを使ってください。

exportは推論用.pthと.indexをoutput/voice-model/へコピーします。
学習再開用G_*.pth、D_*.pthをVC Clientへ登録するものと混同しないでください。
配布物に元音源そのものは含めず、入手URLとハッシュを残しています。
20秒の参照用抜粋はsamples/に含みます。

変換する
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/convert.py input.wav output.wav

オプション：--pitch 0（半音単位）、--index-rate 0.25（0〜1）。
出力先が存在する場合は上書きせず停止します。別名を指定してください。
学習と違い、この変換処理を行うたびにモデルの重みが更新されることはありません。

同梱のテスト音声を作る（任意：libespeak-ng1が必要）
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/make_demo_input.py
  .locals/voice-model/venv/bin/python examples/chukei/voice-model/convert.py output/voice-model/samples/synthetic_input.wav output/voice-model/samples/synthetic_converted.wav

テスト入力はeSpeak NGによる合成音声です。現代人の録音を外部サービスへ
送る工程はありません。生成文は試験音声であることを明示しています。
機械的な入力の抑揚も変換結果に影響するため、人が話した場合の自然さを
このサンプルだけで判断しないでください。

VC Clientで試すとき
RVCに対応したビルドでedit→空きスロット→uploadを開き、出力の.pthと
.indexを指定します。方式RVC v2・40kHz・F0ありを確認してください。
Beatrice専用版ではこのモデルを利用できません。GUI上の項目名・必要入力は
採用版の表示に従ってください。本実験ではRVCのオフライン推論を検証します。

品質の位置付け
約100年前の帯域の狭い録音を使った小規模な実験モデルです。ノイズや
歪みを引き継ぐ可能性があります。本人の声の完全復元や、会話・歌唱・
日本語への対応品質を保証するモデルではありません。実測結果と未検証の
項目をoutput/voice-model/のMODEL_CARD.txtに分けて記録します。

法的・技術的な位置付け
対象話者の追加学習素材はPD録音に限定しました。一方、ソフトと基盤モデル
にはそれぞれのライセンスがあります。全部をまとめてPDとは表記しません。
RIGHTS.txtと同梱ライセンスを残し、生成音声を実在人物の実際の発言として
提示しないでください。
