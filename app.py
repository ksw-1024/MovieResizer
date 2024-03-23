import os
import sys
import json
from logging import getLogger, config

import tkinter as tk
import customtkinter
from tkinter import messagebox

import cv2
import threading

FONT_TYPE = "meiryo"

# ログの準備
with open(os.path.join(os.path.dirname(sys.argv[0]), "utils/log_config.json"), "r") as f:
    log_conf = json.load(f)
        
config.dictConfig(log_conf)
logger = getLogger(__name__)

class App(customtkinter.CTk):
    def __init__(self):
        logger.info("Wake up.")
        super().__init__()

        # メンバー変数の設定
        self.fonts = (FONT_TYPE, 15)
        self.csv_filepath = None

        # フォームのセットアップをする
        self.setup_form()

    def setup_form(self):
        # CustomTkinter のフォームデザイン設定
        customtkinter.set_appearance_mode("dark")  # Modes: system (default), light, dark
        customtkinter.set_default_color_theme("blue")  # Themes: blue (default), dark-blue, green

        # フォームサイズ設定
        self.geometry("640x540")
        self.title("Movie Resizer")
        self.iconbitmap(os.path.join(os.path.dirname(sys.argv[0]), "utils/icon.ico"))

        # 行方向のマスのレイアウトを設定する。リサイズしたときに一緒に拡大したい行をweight 1に設定。
        self.grid_rowconfigure(1, weight=1)
        # 列方向のマスのレイアウトを設定する
        self.grid_columnconfigure(0, weight=1)

        self.title = customtkinter.CTkLabel(self, text="Movie Resizer", fg_color="transparent", font=(FONT_TYPE, 30))
        self.title.grid(row=0, column=0, padx=10, pady=(40,0), sticky="ew")

        # 1つ目のフレームの設定
        # stickyは拡大したときに広がる方向のこと。nsew で4方角で指定する。
        self.read_file_frame = ReadFileFrame(master=self, header_name="ファイル読み込み")
        self.read_file_frame.grid(row=1, column=0, padx=20, pady=(0,20), sticky="ew")

class fileLists:
    List = []
    output_dir = ""

class SelectQuality(customtkinter.CTkFrame):
    def __init__(self, master, title, values):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.title = title
        self.radiobuttons = []
        self.variable = customtkinter.StringVar(value="")

        self.title = customtkinter.CTkLabel(self, text=self.title, fg_color="gray30", corner_radius=6, font=(FONT_TYPE,20))
        self.title.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

        for i, value in enumerate(self.values):
            radiobutton = customtkinter.CTkRadioButton(self, text=value, value=value, variable=self.variable, state="disabled")
            radiobutton.grid(row=i + 1, column=0, padx=10, pady=(10,10), sticky="w")
            self.radiobuttons.append(radiobutton)
        
        self.radiobuttons[0].select()

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)

class ReadFileFrame(customtkinter.CTkFrame, fileLists):
    def __init__(self, *args, header_name="ReadFileFrame", **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fonts = (FONT_TYPE, 15)
        self.header_name = header_name

        self.setup_form()

    def setup_form(self):
        # 行方向のマスのレイアウトを設定する。リサイズしたときに一緒に拡大したい行をweight 1に設定。
        self.grid_rowconfigure(0, weight=1)
        # 列方向のマスのレイアウトを設定する
        self.grid_columnconfigure(0, weight=1)

        # フレームのラベルを表示
        self.label = customtkinter.CTkLabel(self, text=self.header_name, font=(FONT_TYPE, 11))
        self.label.grid(row=0, column=0, padx=20, sticky="w")

        # ファイルパスを指定するテキストボックス。これだけ拡大したときに、幅が広がるように設定する。
        self.textbox = customtkinter.CTkEntry(master=self, placeholder_text="ファイルを読み込む", width=120, font=self.fonts)
        self.textbox.grid(row=1, column=0, padx=10, pady=(0,10), sticky="ew")

        # ファイル選択ボタン
        self.button_select = customtkinter.CTkButton(master=self, 
            fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),   # ボタンを白抜きにする
            command=self.button_select_callback, text="ファイル選択", font=self.fonts)
        self.button_select.grid(row=1, column=1, padx=10, pady=(0,10))

        # 画質選択
        self.selectQuality_frame = SelectQuality(self, "画質選択", values=["144p","240p","360p","720p"])
        self.selectQuality_frame.grid(row=2, column=0, columnspan=2, padx=(10, 10), pady=(10, 10), sticky="nsew")

        # 実行ボタン
        self.button_open = customtkinter.CTkButton(master=self, command=self.button_open_callback, text="動画ファイルを選択してください", font=self.fonts, state="disabled")
        self.button_open.grid(row=3, column=0, padx=10, pady=(40,20), sticky="ew", columnspan=2)

        self.progressbar = customtkinter.CTkProgressBar(self, orientation="horizontal")
        self.progressbar.grid(row=4, column=0, columnspan=2, pady=10, padx=10, sticky="ew")
        self.progressbar.set(0)

    def button_select_callback(self):
        """
        選択ボタンが押されたときのコールバック。ファイル選択ダイアログを表示する
        """        
        # エクスプローラーを表示してファイルを選択する
        file_names = ReadFileFrame.file_read()

        if file_names is not None:
            fileLists.List = file_names
            # ファイルパスをテキストボックスに記入
            self.textbox.delete(0, tk.END)
            for file_name in file_names:
                self.textbox.insert(0, "[" + os.path.basename(file_name) + "]")
            
            self.button_open.configure(text="変換を実行", state="normal")
            for s in self.selectQuality_frame.radiobuttons:
                s.configure(state="normal")

    def button_open_callback(self):
        """
        実行ボタンが押されたときのコールバック。
        """

        quality = self.selectQuality_frame.get()
        fileLists.output_dir = ReadFileFrame.dir_read()
        if fileLists.output_dir is None:
            return
        
        logger.info("Start conversion to " + quality + ".")
        thread = threading.Thread(target=self.resizer, args=(quality,))
        thread.daemon = True
        thread.start()
        self.button_open.configure(text="処理中です。", state="disabled")
        self.button_select.configure(state="disabled")
        for s in self.selectQuality_frame.radiobuttons:
            s.configure(state="disabled")

    def resizer(self,quality):
        quality = int(quality[:-1])
        logger.info("Picture quality is set to " + str(quality) + ".")

        totalframe = 0
        doneframe = 0

        # すべての動画の総フレーム数を取得
        for f in fileLists.List:
            cv = cv2.VideoCapture(f)
            totalframe = totalframe + int(cv.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info("Total Frame Count => " + str(totalframe))

        for index, file in enumerate(fileLists.List):
            filename = os.path.splitext(os.path.basename(file))[0]

            logger.info("Create a file list.")
            logger.info("No." + str(index+1) + " file => " + file)

            video = cv2.VideoCapture(file)
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            framerate = float(video.get(cv2.CAP_PROP_FPS))
            framecount = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

            logger.info("Total number of frame rate for the No." + str(index+1) + " video => " + str(framecount))

            new_height = quality
            new_width = int(width * (new_height / height))

            logger.info("Output directory => " + fileLists.output_dir)

            output_video = cv2.VideoWriter(fileLists.output_dir + "/" + filename + ".mp4", cv2.VideoWriter_fourcc(*'mp4v'),framerate,(new_width, new_height))

            logger.info("Start exporting.")

            while True:
                ret, frame = video.read()
                if not ret:
                    break
                resized_frame = cv2.resize(frame, (new_width, new_height))
                output_video.write(resized_frame)
                doneframe = doneframe + 1
                percent = doneframe / totalframe

                if(1 > percent):
                    self.progressbar.set(float('{:.3f}'.format(percent)))
                    self.button_open.configure(text="処理中です。" + str(float('{:.3f}'.format(percent * 100))) + "%完了")
                else:
                    self.progressbar.set(1)

            video.release()
            output_video.release()

            logger.critical("Successful export.")

        logger.info("All videos are successfully processed.")
        self.button_open.configure(text="処理が完了しました。")
        self.progressbar.set(1)
        self.button_select.configure(state="normal")
        for s in self.selectQuality_frame.radiobuttons:
            s.configure(state="normal")
        
    @staticmethod
    def file_read():
        """
        ファイル選択ダイアログを表示する
        """
        current_dir = os.path.abspath(os.path.dirname(__file__))
        file_pathes = tk.filedialog.askopenfilenames(title="変換したい動画ファイルを選択", filetypes=[("動画ファイル","*.mp4"),("動画ファイル","*.mov"),("動画ファイル","*.mkv")],initialdir=current_dir)

        if len(file_pathes) != 0:
            return file_pathes
        else:
            # ファイル選択がキャンセルされた場合
            return None
        
    @staticmethod
    def dir_read():
        """
        ディレクトリ選択ダイアログ
        """
        current_dir = os.path.abspath(os.path.dirname(__file__))
        dir_path = tk.filedialog.askdirectory(title="書き出し先を選択", initialdir=current_dir)

        if len(dir_path) != 0:
            return dir_path
        else:
            return None

if __name__ == "__main__":        
    app = App()

    def appClose():
        if messagebox.askokcancel("確認", "本当に閉じていいですか？"):
            app.destroy()
            app.quit()
            sys.exit()
    
    app.protocol("WM_DELETE_WINDOW", appClose)
    app.mainloop()