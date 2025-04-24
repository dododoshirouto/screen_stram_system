import os
import subprocess
import sys
import time
import json
import threading
import tkinter as tk
import tkinter.simpledialog as sd
import pystray
from pystray import Menu, MenuItem
from PIL import Image
from cv2 import resize as cv2resize, INTER_AREA, INTER_NEAREST
from numpy import array as nparray
from mss import mss
from subprocess import Popen, PIPE, CREATE_NO_WINDOW
from enum import Enum
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]

# キーをファイルに保存・読み込み
def load_stream_key():
    try:
        with open("stream_key.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "xxxx-xxxx-xxxx-xxxx"  # デフォルト値

def load_youtube_token():
    try:
        return Credentials.from_authorized_user_file("youtube_token.json", YOUTUBE_SCOPES)
    except Exception:
        return None

def lead_stream_info():
    try:
        with open("stream_info.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "title": "作業アーカイブ",
            "privacyStatus": "unlisted"
        }  # デフォルト値

def save_stream_key(key):
    with open("stream_key.txt", "w", encoding="utf-8") as f:
        f.write(key)

def save_stream_info(info):
    with open("stream_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

class CODEC(Enum):
    h264 = "libx264"
    h265 = "libx265"
    av1  = "libsvtav1"
    NVENC_h264 = "h264_nvenc"
    NVENC_HEVC = "nvenc_hevc"

class ScreenStream:
    def __init__(
        self,
        rtmp_url="rtmp://localhost/live1/",
        stream_key="tokaisodachi",
        framerate=30,
        resolution_h=1080,
        codec=CODEC.h264,
        bitrate=4500,
        crf=30,
        preset="ultrafast",
        cpu_used=8,
        tray=None
    ):
        self.tray:TrayApp = tray
        self.rtmp_url = rtmp_url
        self.stream_key = stream_key
        self.framerate = framerate
        self.resolution_h = resolution_h
        self.codec = codec
        self.bitrate = bitrate
        self.crf = crf
        self.preset = preset
        self.cpu_used = cpu_used

        self.broadcast_id = None

        with mss() as tmp_sct:
            monitor = tmp_sct.monitors[1]
            screen_width = monitor["width"]
            screen_height = monitor["height"]

        self.resolution_w = int(screen_width * (self.resolution_h / screen_height))
        if self.resolution_w % 2 != 0:
            self.resolution_w += 1

        self.process = None
        self.stop_flag = False
        self.mode = "normal"

        self.creds = load_youtube_token()

        (self.title, self.privacyStatus) = lead_stream_info().values()

    def start_stream(self):
        if self.process is not None:
            print("もう配信中だよ")
            return

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.resolution_w}x{self.resolution_h}",
            "-r", str(self.framerate),
            "-i", "-",
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", self.codec.value,
            "-preset", str(self.preset),
            "-pix_fmt", "yuv420p",
            "-g", str(self.framerate*2),
            "-tune", "zerolatency",
            "-bf", "2",
        ]

        if self.codec in [CODEC.h264, CODEC.h265, CODEC.NVENC_h264, CODEC.NVENC_HEVC]:
            ffmpeg_cmd += [
                "-b:v", f"{self.bitrate}k",
                "-maxrate", f"{self.bitrate}k",
                "-bufsize", f"{self.bitrate*2}k"
            ]
        else:
            ffmpeg_cmd += ["-crf", str(self.crf)]

        if self.codec == CODEC.av1:
            ffmpeg_cmd += ["-cpu-used", str(self.cpu_used)]

        ffmpeg_cmd += [
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            self.rtmp_url + self.stream_key
        ]
        print("配信コマンド:", ffmpeg_cmd)

        self.stop_flag = False
        
        startupinfo = None
        if os.name == 'nt':  # only the OS is Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        self.process = Popen(ffmpeg_cmd, stdin=PIPE, startupinfo=startupinfo)
        #self.process = Popen(ffmpeg_cmd, stdin=PIPE, creationflags=CREATE_NO_WINDOW) #Alternative Method
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        self.tray._update_menu()
        self.tray.set_icon(stream=True)
        print("配信開始したよ")

    def stop_stream(self):
        if self.process is None:
            print("配信してないよ")
            return
        print("配信停止するね")
        self.stop_flag = True
        if self.process.stdin:
            self.process.stdin.close()
        self.process.terminate()
        self.process.wait()
        self.process = None

    def set_stream_key(self, key):
        self.stream_key = key
        print(f"ストリームキーを {key} に変更したよ")

    def set_mode(self, mode):
        self.mode = mode
        print(f"モードを {mode} に切り替えたよ")

    def _capture_loop(self):
        frame_count = 0
        start_time = time.time()

        try:
            with mss() as cap_sct:
                monitor = cap_sct.monitors[1]
                while not self.stop_flag:
                    frame = nparray(cap_sct.grab(monitor))[:, :, :3]
                    frame = cv2resize(frame, (self.resolution_w, self.resolution_h), interpolation=INTER_AREA)
                    if self.mode == "mosaic":
                        small = cv2resize(frame, (self.resolution_w // 30, self.resolution_h // 30), interpolation=INTER_AREA)
                        frame = cv2resize(small, (self.resolution_w, self.resolution_h), interpolation=INTER_NEAREST)
                    elif self.mode == "black":
                        frame[:] = 0
                    self.process.stdin.write(frame.tobytes())

                    # --- ここでフレーム送信のペースを調整 ---
                    frame_count += 1
                    # 何フレーム目かに応じて「本来の再生時間」を計算
                    ideal_time = frame_count / self.framerate  
                    current_time = time.time() - start_time
                    # まだ再生時間に達してなければ、ちょっと待つ
                    if current_time < ideal_time:
                        time.sleep(ideal_time - current_time)

        except Exception as e:
            print("配信ループでエラー:", e)
        finally:
            print("配信ループ終了")
    

    def create_youtube_broadcast_and_start(self):
        if not self.creds or not self.creds.valid:
            print("YouTubeにログインしてないっぽい")
            return

        youtube = googleapiclient.discovery.build("youtube", "v3", credentials=self.creds)

        # 1. ライブ配信枠を作成
        broadcast_request = youtube.liveBroadcasts().insert(
            part="snippet,status,contentDetails",
            body={
                "snippet": {
                    "title": self.title,
                    "scheduledStartTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + 60)),  # 1分後
                    "description": "",
                },
                "status": {
                    "privacyStatus": self.privacyStatus
                },
                "contentDetails": {
                    "enableAutoStart": True,
                    "enableAutoStop": False
                }
            }
        ).execute()

        self.broadcast_id = broadcast_request["id"]
        print("Broadcast ID:", self.broadcast_id)

        # 2. ストリーム作成
        stream_request = youtube.liveStreams().insert(
            part="snippet,cdn",
            body={
                "snippet": {
                    "title": self.title
                },
                "cdn": {
                    "frameRate": "30fps",
                    "resolution": "720p",
                    "ingestionType": "rtmp"
                }
            }
        ).execute()

        stream_id = stream_request["id"]
        stream_info = stream_request["cdn"]["ingestionInfo"]
        self.rtmp_url = stream_info["ingestionAddress"] + "/"
        self.stream_key = stream_info["streamName"]
        print("RTMP:", self.rtmp_url + self.stream_key)

        # 3. バインド
        youtube.liveBroadcasts().bind(
            part="id,contentDetails",
            id=self.broadcast_id,
            streamId=stream_id
        ).execute()

        # 4. ffmpegで配信スタート
        self.start_stream()

        # 5. 配信枠を live 状態に移行
        youtube.liveBroadcasts().transition(
            broadcastStatus="live",
            id=self.broadcast_id,
            part="status"
        ).execute()

        print("YouTubeライブを開始したよ！")
        self.tray._update_menu()

    def stop_stream(self):
        if self.process is None:
            print("配信してないよ")
            return
        print("配信停止するね")
        self.stop_flag = True
        if self.process.stdin:
            self.process.stdin.close()
        self.process.terminate()
        self.process.wait()
        self.process = None

        # 配信枠も終了させる
        if hasattr(self, "broadcast_id") and self.creds:
            try:
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=self.creds)
                youtube.liveBroadcasts().transition(
                    broadcastStatus="complete",
                    id=self.broadcast_id,
                    part="status"
                ).execute()
                print("YouTube配信枠も終了したわ")
            except Exception as e:
                print("配信枠終了時にエラー:", e)

        self.tray._update_menu()



class TrayApp:
    def __init__(self):
        # PyInstallerでパスを解決するときの対応:
        if hasattr(sys, '_MEIPASS'):
            # PyInstallerで固めたexeから実行されている場合
            base_path = sys._MEIPASS
        else:
            # 普通にPythonで実行している場合
            base_path = os.path.dirname(__file__)
            
        off_icon_path = os.path.join(base_path, "icons", "off.png")
        on_icon_path  = os.path.join(base_path, "icons", "on.png")
        mosaic_icon_path = os.path.join(base_path, "icons", "mosaic.png")
        black_icon_path  = os.path.join(base_path, "icons", "black.png")

        self.icon_off = Image.open(off_icon_path)
        self.icon_on = Image.open(on_icon_path)
        self.icon_mosaic = Image.open(mosaic_icon_path)
        self.icon_black = Image.open(black_icon_path)

        # 起動時にファイルからキーを読み込む
        default_key = load_stream_key()
        self.streamer = ScreenStream(
            rtmp_url="rtmp://a.rtmp.youtube.com/live2/",
            stream_key=default_key,
            framerate=8,
            resolution_h=720,
            codec=CODEC.h264,
            crf=30,
            bitrate=3000,
            preset=5,
            tray=self
        )

        # アイコンは初期オフ状態で
        self.icon = pystray.Icon(
            "ScreenStreamer",
            self.icon_off,
            menu=self.build_menu()
        )

    def build_menu(self):
        """現在のモードを見てメニューのラベルを動的に変える"""
        # ラベル生成用のヘルパ
        def mode_label(mode_value, text):
            return ("● " if self.streamer.mode == mode_value else "　") + text
        
        def privacy_label(privacy_value, text):
            return ("▶ " if self.streamer.privacyStatus == privacy_value else "　") + text

        return Menu(
            MenuItem("配信開始" if (self.streamer.process is None) else "配信停止", self.on_start if (self.streamer.process is None) else self.on_stop, enabled=not(not self.streamer.creds or not self.streamer.creds.valid)),
            # MenuItem("ストリームキー変更", self.on_change_key),
            MenuItem(
                "モード: " + {"normal": "普通", "mosaic": "モザイク", "black": "暗転"}[self.streamer.mode],
                Menu(
                    MenuItem(mode_label("normal", "普通"), self.on_mode_normal),
                    MenuItem(mode_label("mosaic", "モザイク"), self.on_mode_mosaic),
                    MenuItem(mode_label("black", "暗転"), self.on_mode_black),
                )
            ),
            MenuItem("ログイン" if (not self.streamer.creds or not self.streamer.creds.valid) else "ログイン済み", self.login_youtube, enabled=(not self.streamer.creds or not self.streamer.creds.valid)),
            MenuItem(
                "配信情報",
                Menu(
                    MenuItem("タイトル: " + self.streamer.title, self.on_change_title),
                    MenuItem(
                        "モード: " + {"public": "公開", "unlisted": "限定公開", "private": "非公開"}[self.streamer.privacyStatus],
                        Menu(
                            MenuItem(privacy_label("public", "公開"), lambda _: self.on_privacy("public")),
                            MenuItem(privacy_label("unlisted", "限定公開"), lambda _: self.on_privacy("unlisted")),
                            MenuItem(privacy_label("private", "非公開"), lambda _: self.on_privacy("private")),
                        )
                    )
                )
            ),
            MenuItem("終了", self.on_quit)
        )
    
    def set_icon(self, stream=True):
        if stream:
            if self.streamer.mode == "normal":
                self.icon.icon = self.icon_on
            elif self.streamer.mode == "mosaic":
                self.icon.icon = self.icon_mosaic
            elif self.streamer.mode == "black":
                self.icon.icon = self.icon_black
        else:
            self.icon.icon = self.icon_off
        self.icon.update_menu()

    def run(self):
        self.icon.run()

    def on_start(self, _):
        # self.streamer.start_stream()
        self.streamer.create_youtube_broadcast_and_start()
        self.set_icon(stream=self.streamer.process is not None)
        self._update_menu()

    def on_stop(self, _):
        self.streamer.stop_stream()
        self.set_icon(stream=self.streamer.process is not None)
        self._update_menu()

    def on_change_key(self, _):
        def ask_key():
            root = tk.Tk()
            root.withdraw()
            # 今のキーを初期値に設定
            new_key = sd.askstring(
                "キー変更",
                "ストリームキーを入力して",
                initialvalue=self.streamer.stream_key
            )
            if new_key:
                self.streamer.set_stream_key(new_key)
                # 入力されたキーを保存
                save_stream_key(new_key)
            root.destroy()

        threading.Thread(target=ask_key, daemon=True).start()

    def on_mode_normal(self, _):
        self.streamer.set_mode("normal")
        self.set_icon(stream=self.streamer.process is not None)
        self._update_menu()

    def on_mode_mosaic(self, _):
        self.streamer.set_mode("mosaic")
        self.set_icon(stream=self.streamer.process is not None)
        self._update_menu()

    def on_mode_black(self, _):
        self.streamer.set_mode("black")
        self.set_icon(stream=self.streamer.process is not None)
        self._update_menu()

    def on_quit(self, _):
        self.streamer.stop_stream()
        self.icon.stop()
        sys.exit(0)

    def _update_menu(self):
        """メニューを最新状態に更新する"""
        self.icon.menu = self.build_menu()
        self.icon.update_menu()

    def login_youtube(self):
        if not self.streamer.creds or not self.streamer.creds.valid:
            if self.streamer.creds and self.streamer.creds.expired and self.streamer.creds.refresh_token:
                self.streamer.creds.refresh(Request())
            else:
                try:
                    client_secret = os.path.join(sys._MEIPASS, "client_secret_458758854605-ihia8ttepcfjeab3k80lk1rc40dttso9.apps.googleusercontent.com.json") if hasattr(sys, '_MEIPASS') else "client_secret_458758854605-ihia8ttepcfjeab3k80lk1rc40dttso9.apps.googleusercontent.com.json"
                    if os.path.exists("client_secret.json"):
                        client_secret = "client_secret.json"
                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        client_secret,
                        YOUTUBE_SCOPES
                    )
                    self.streamer.creds = flow.run_local_server(port=0)
                except Exception as e:
                    import traceback
                    with open("error.log", "w", encoding="utf-8") as f:
                        f.write(traceback.format_exc())

            # 取得したトークンを保存
            with open("youtube_token.json", "w") as token:
                token.write(self.streamer.creds.to_json())
        self._update_menu()
    
    def on_change_title(self, _):
        def ask_title():
            root = tk.Tk()
            root.withdraw()
            # 今のタイトルを初期値に設定
            new_title = sd.askstring(
                "タイトル変更",
                "タイトルを入力してね",
                initialvalue=self.streamer.title
            )
            if new_title:
                self.streamer.title = new_title
                save_stream_info({
                    "title": self.streamer.title,
                    "privacyStatus": self.streamer.privacyStatus
                })
            root.destroy()
            self._update_menu()
        threading.Thread(target=ask_title, daemon=True).start()
        
    def on_privacy(self, privacy_value:pystray._win32.Icon):
        self.streamer.privacyStatus = privacy_value
        save_stream_info({
            "title": self.streamer.title,
            "privacyStatus": self.streamer.privacyStatus
        })
        self._update_menu()


def main():
    tray_app = TrayApp()
    tray_app.run()

if __name__ == "__main__":
    main()
