# Screen Stream System

![image](https://github.com/user-attachments/assets/18e84e7e-dcb8-4856-b53d-1c9a13cf67d9)


## 全画面をYouTubeLiveに送信するだけのアプリ

### インストール

`screen_stream.exe`をダウンロード
[screen_stream.exe](https://github.com/dododoshirouto/screen_stram_system/releases/download/ver.1.1/screen_stream.exe)

FFmpegをインストールする
[WindowsにFFmpegをインストールする方法](https://qiita.com/Tadataka_Takahashi/items/9dcb0cf308db6f5dc31b)

ダウンロードした`screen_stream.exe`を開く

### 概要

ワンクリックで配信が開始できます
普段の作業画面のアーカイブ化とかに使えんかなーと思って

2025/04/25
YouTubeAPIでログインして枠立てをするようにしたので、より確実に配信が始まります！！！

### 使い方

1. `screen_stream.exe`を実行する
2. タスクトレイのなんか黒いテレビのアイコンを右クリック
3. YouTubeでログイン（初回だけ）
4. 配信タイトルと公開設定を選ぶ
5. 配信開始を押す
6. 配信されてると思うから、YouTubeStudioで確認して！

### 機能

#### 画面モザイク機能

タスクトレイアイコンを右クリックして、モードを開くと、モザイクや暗転のモードが選べるよ

コンプラ注意！！！

#### 以上！！

漢に面倒な設定は不要！！

デフォルト設定は以下の通り
```python
framerate=8,
resolution_h=720,
codec=CODEC.h264,
crf=30,
bitrate=2000,
preset=5,
```

設定変えたい人は、`screen_stream.py`を書き換えてビルドしてね

### 免責

このアプリや、このアプリを元としたシステム等を使用することで発生するいかなるすべての人の不利益に対して責任を取ることはできません。

画面に映るものに注意し、真摯な紳士としてご利用下さい。（淑女の方でも歓迎です）

### ライセンス

よくわからんけどMIT

ただしアイコン画像の自作発言はやめて下さい。どこまでも追いかけます。

アイコン画像のみ (c) どどど素人 dododo-shirouto 2025
