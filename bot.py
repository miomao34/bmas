from typing import List
from os import getenv, listdir
from string import punctuation
import subprocess
import asyncio
from urllib.parse import urlencode

from telegram import InlineQueryResultAudio, Update
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    InlineQueryHandler,
    ContextTypes,
)

import uvicorn
from fastapi import FastAPI, Response
from starlette.middleware.cors import CORSMiddleware

PATH = "./vox/"


class BMAS:
    fa_app: FastAPI
    server: uvicorn.Server
    tg_app: Application

    vox: dict

    special_converts = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine",
        # TODO: tokens past here aren't converted correctly yet
        "10": "ten",
        "11": "eleven",
        "12": "twelve",
        "13": "thirteen",
        "14": "fourteen",
        "15": "fifteen",
        "16": "sixteen",
        "17": "seventeen",
        "18": "eighteen",
        "19": "nineteen",
        "20": "twenty",
        "30": "thirty",
        "40": "fourty",
        "50": "fifty",
        "60": "sixty",
        "70": "seventy",
        "80": "eighty",
        "90": "ninety",
    }

    def __init__(self) -> None:
        self.vox = {}
        print("init, innit")

        self.env_vars = {
            "IP": None,
            "PORT": None,
            "TELEGRAM_TOKEN": None,
            "TELEGRAM_LOG_ID": None,
        }

        for var_name in self.env_vars.keys():
            new_var = getenv(var_name)
            if not new_var:
                raise ValueError(f"didn't set an env var: {var_name}")
            self.env_vars[var_name] = new_var

        for i in ["PORT", "TELEGRAM_LOG_ID"]:
            self.env_vars[i] = int(self.env_vars[i])

        for filename in listdir(PATH):
            filename_no_ext = filename.split(".")[0]
            filepath = PATH + filename
            print(f"loading '{filepath}'...", end="")
            self.vox[filename_no_ext] = filepath
            print("done")

        print(sorted(self.vox.keys()))

        self.fa_app = FastAPI()
        self.fa_app.add_api_route("/render", self.render, methods=["GET"])
        self.fa_app.add_api_route("/ping", self.ping, methods=["GET"])

        self.fa_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.server = uvicorn.Server(
            config=uvicorn.Config(
                app=self.fa_app,
                port=self.env_vars["PORT"],
                host=self.env_vars["IP"],
            )
        )

        self.tg_app = (
            ApplicationBuilder().token(self.env_vars["TELEGRAM_TOKEN"]).build()
        )
        self.tg_app.add_handler(InlineQueryHandler(self.inline_render))
        self.tg_app.add_handler(CommandHandler("start", self.start))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = [
            "Hello and welcome to the Black Mesa research facility.",
            # "Use /vox to get a BMAS message",
            "Try it in inline mode!",
        ]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="\n".join(text),
        )

        await context.bot.send_message(
            chat_id=self.env_vars["TELEGRAM_LOG_ID"],
            text=f"new user! {update.effective_user.full_name}: @{update.effective_user.username}",
        )

    async def init_async(self) -> None:
        await self.tg_app.initialize()
        await self.tg_app.start()
        await self.tg_app.updater.start_polling()

    async def stop_async(self) -> None:
        await self.tg_app.updater.stop()
        await self.tg_app.stop()
        await self.tg_app.shutdown()

    async def inline_render(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.inline_query.query
        if not query:
            return

        results = [
            InlineQueryResultAudio(
                id="BMAS",
                title=query,
                audio_url=self.env_vars["IP"]
                + f":{self.env_vars['PORT']}"
                + "/render?"
                + urlencode({"sentence": query}),
            )
        ]

        # await context.bot.send_message(
        #     chat_id=self.env_vars["TELEGRAM_LOG_ID"],
        #     text=f"inline render! {update.effective_user.full_name}: @{update.effective_user.username}\n{query}",
        # )

        await context.bot.answer_inline_query(update.inline_query.id, results)

    @staticmethod
    def tokenize_string(input: str) -> List[str]:
        # removing punctuation
        # TODO: floats?
        input = input.translate(punctuation)
        # to lowercase
        input = input.lower()
        # to tokens
        return input.split()

    @staticmethod
    def intable(input: str) -> bool:
        try:
            int(input)
            return True
        except:
            return False

    def convert_int(self, input: str) -> bytes:
        result = []
        for digit in input:
            translated_digit = self.special_converts[digit]
            result.append(self.vox[translated_digit])

        return result

    def convert_float(self, input: str) -> bytes:
        result = []
        for digit in input:
            translated_digit = self.special_converts[digit]
            result.append(self.vox[translated_digit])

        return result

    async def ping(self) -> Response:
        return Response("ok")

    async def render(self, sentence: str = "") -> Response:
        if not sentence:
            return

        tokens = self.tokenize_string(sentence)

        result = []
        for token in tokens:
            if self.intable(token):
                result.extend(self.convert_int(token))
                continue

            if token not in self.vox:
                continue

            result.append(self.vox[token])

        # ???
        print(result)
        # fmt: off
        command = [
            "ffmpeg",
            "-hide_banner",
            "-v", "error",
            "-i", "concat:" + "|".join(result),
            "-acodec", "copy",
            "-y", "out.mp3",
        ]
        print(command)
        subprocess.run(command).check_returncode()
        # fmt: on

        f = open("out.mp3", "rb")
        result_bytes = f.read()
        f.close()

        return Response(result_bytes, media_type="audio/mpeg")


# bot = Bot(token=TOKEN)
# update_queue = Queue()
# dp = Dispatcher(bot, update_queue, use_context=True)
# # Add handlers
# dp.add_handler(CommandHandler("start", start))
# dp.add_handler(InlineQueryHandler(inline_query))
# dp.add_handler(MessageHandler(Filters.text, message))


# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )


async def main():
    bmas = BMAS()

    await bmas.init_async()

    await bmas.server.serve()

    await bmas.stop_async()


if __name__ == "__main__":
    asyncio.run(main())
