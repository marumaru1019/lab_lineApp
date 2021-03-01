import os
import sys
from linebot import (
    LineBotApi, WebhookHandler
)


from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
import logging

import json

import pandas as pd
import boto3
import datetime
import pytz
from io import StringIO

from linebot.models import *


# lineが登録されたときに行われるイベント
def create_new(usrid, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))

    # ユーザーIDがある場合は登録を拒否
    if usrid in list(df["ユーザーID"]):
        dupiricate_message = "すでに{}様は澤田研究室の見学名簿に登録されています。\n確認から名簿があるか確認してみてください。".format(
            username)
        return dupiricate_message

    # ユーザーIDがない場合には登録を許可
    elif usrid not in list(df["ユーザーID"]):
        # 取得したユーザー情報を元にcsvを更新
        s3_resource = boto3.resource('s3')
        new_dt = pd.DataFrame([[usrid, dt_now.strftime(
            '%Y/%m/%d'), dt_now.strftime('%H:%M'), username, "", ""]], columns=col)
        df2 = df.append(new_dt, ignore_index=True)

        s3_object = s3_resource.Object(BUCKET_NAME, KEY)
        s3_object.put(Body=df2.to_csv(None, index=False).encode('utf_8_sig'))

        reg_text = '''登録ありがとうございました
これより研究室の見学の登録などが行なえます。
日程とメールアドレスを登録して澤田研究室に見学に来てみよう!'''
        return reg_text


# 日付を獲得する処理
def get_date(date_str, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # 名前が登録されているユーザーの場合
    try:
        # ユーザーが居るとき
        if username in list(df["名前"]):
            # usernameを含まない行の取り出し
            df_ori = df[df["名前"] != username]
            # usernameを含む行の取り出し→処理ではこっちをつかう
            df_user = df[df["名前"] == username]

            # 日程希望を登録
            df_user.希望日時 = date_str

            # データを再合成
            df2 = pd.concat([df_ori, df_user])

            # 取得した体重を元にcsvを更新
            s3_resource = boto3.resource('s3')

            s3_object = s3_resource.Object(BUCKET_NAME, KEY)
            s3_object.put(Body=df2.to_csv(
                None, index=False).encode('utf_8_sig'))

            # 終了を知らせるメッセージ
            complete_text = "{}様の日程を{}で承りました".format(username, date_str)
            return complete_text
        # ユーザーがいないとき
        else:
            fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
            return fail_text

    # usernameがなかったときの処理
    except:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text

# メール・アドレスを取得した際の処理


def get_mail(mail_text, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # 名前が登録されているユーザーの場合
    try:
        if username in list(df["名前"]):
            # usernameを含まない行の取り出し
            df_ori = df[df["名前"] != username]
            # usernameを含む行の取り出し→処理ではこっちをつかう
            df_user = df[df["名前"] == username]

            # 日程希望を登録
            df_user.メールアドレス = mail_text

            # データを再合成
            df2 = pd.concat([df_ori, df_user])

            # 取得したメールを元にcsvを更新
            s3_resource = boto3.resource('s3')

            s3_object = s3_resource.Object(BUCKET_NAME, KEY)
            s3_object.put(Body=df2.to_csv(
                None, index=False).encode('utf_8_sig'))

            # 終了を知らせるメッセージ
            complete_text = "{}様のメールアドレスを{}で承りました".format(username, mail_text)
            return complete_text
        else:
            fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
            return fail_text

    # usernameがなかったときの処理
    except:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text

# ユーザー情報の確認


def show_user(username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # ユーザーネームがあることが最低条件
    if username in list(df["名前"]):
        df_user = df[df["名前"] == username]
        df_user = df_user.reset_index()
        shere = '''
名前:{}
希望日時:{}
メールアドレス:{}

で登録いただいております。
訂正したい場合、再度日程またはメールアドレスから上書きを行ってください。
'''.format(df_user["名前"][0], df_user["希望日時"][0].replace("T", " "), df_user["メールアドレス"][0])
        return shere
    # ユーザーネームがない場合
    else:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text


BUCKET_NAME = "pypy-test"
KEY = "kenken.csv"
dt_now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

col = ["ユーザーID", '登録日', '時間', '名前', '希望日時', 'メールアドレス']


channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# lineが登録されたときに行われるイベント


def create_new(usrid, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))

    # ユーザーIDがある場合は登録を拒否
    if usrid in list(df["ユーザーID"]):
        dupiricate_message = "すでに{}様は澤田研究室の見学名簿に登録されています。\n確認から名簿があるか確認してみてください。".format(
            username)
        return dupiricate_message

    # ユーザーIDがない場合には登録を許可
    elif usrid not in list(df["ユーザーID"]):
        # 取得したユーザー情報を元にcsvを更新
        s3_resource = boto3.resource('s3')
        new_dt = pd.DataFrame([[usrid, dt_now.strftime(
            '%Y/%m/%d'), dt_now.strftime('%H:%M'), username, "", ""]], columns=col)
        df2 = df.append(new_dt, ignore_index=True)

        s3_object = s3_resource.Object(BUCKET_NAME, KEY)
        s3_object.put(Body=df2.to_csv(None, index=False).encode('utf_8_sig'))

        reg_text = '''登録ありがとうございました
これより研究室の見学の登録などが行なえます。
日程とメールアドレスを登録して澤田研究室に見学に来てみよう!'''
        return reg_text


# 日付を獲得する処理
def get_date(date_str, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # 名前が登録されているユーザーの場合
    try:
        # ユーザーが居るとき
        if username in list(df["名前"]):
            # usernameを含まない行の取り出し
            df_ori = df[df["名前"] != username]
            # usernameを含む行の取り出し→処理ではこっちをつかう
            df_user = df[df["名前"] == username]

            # 日程希望を登録
            df_user.希望日時 = date_str

            # データを再合成
            df2 = pd.concat([df_ori, df_user])

            # 取得した体重を元にcsvを更新
            s3_resource = boto3.resource('s3')

            s3_object = s3_resource.Object(BUCKET_NAME, KEY)
            s3_object.put(Body=df2.to_csv(
                None, index=False).encode('utf_8_sig'))

            # 終了を知らせるメッセージ
            complete_text = "{}様の日程を{}で承りました".format(username, date_str)
            return complete_text
        # ユーザーがいないとき
        else:
            fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
            return fail_text

    # usernameがなかったときの処理
    except:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text

# メール・アドレスを取得した際の処理


def get_mail(mail_text, username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # 名前が登録されているユーザーの場合
    try:
        if username in list(df["名前"]):
            # usernameを含まない行の取り出し
            df_ori = df[df["名前"] != username]
            # usernameを含む行の取り出し→処理ではこっちをつかう
            df_user = df[df["名前"] == username]

            # 日程希望を登録
            df_user.メールアドレス = mail_text

            # データを再合成
            df2 = pd.concat([df_ori, df_user])

            # 取得したメールを元にcsvを更新
            s3_resource = boto3.resource('s3')

            s3_object = s3_resource.Object(BUCKET_NAME, KEY)
            s3_object.put(Body=df2.to_csv(
                None, index=False).encode('utf_8_sig'))

            # 終了を知らせるメッセージ
            complete_text = "{}様のメールアドレスを{}で承りました".format(username, mail_text)
            return complete_text
        else:
            fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
            return fail_text

    # usernameがなかったときの処理
    except:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text

# ユーザー情報の確認


def show_user(username):
    # lineのユーザー情報を登録する
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    body = obj['Body']
    csv_string = body.read().decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    # ユーザーネームがあることが最低条件
    if username in list(df["名前"]):
        df_user = df[df["名前"] == username]
        df_user = df_user.reset_index()
        shere = '''
名前:{}
希望日時:{}
メールアドレス:{}

で登録いただいております。
訂正したい場合、再度日程またはメールアドレスから上書きを行ってください。
'''.format(df_user["名前"][0], df_user["希望日時"][0].replace("T", " "), df_user["メールアドレス"][0])
        return shere
    # ユーザーネームがない場合
    else:
        fail_text = "{}様は澤田研究室に登録されていません\n登録し直してください".format(username)
        return fail_text

