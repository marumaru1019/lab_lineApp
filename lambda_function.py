from component import *

# 期間内, 期間外を設定する変数
inner_date = True

BUCKET_NAME = "pypy-test"
KEY = "kenken.csv"
dt_now = datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

col = ["ユーザーID", '登録日', '時間', '名前', '希望日時', 'メールアドレス']


# lineのアクセスシークレットとトークンが設定されているか確認
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)


# アクセストークンとアクセスシークレットをセット
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


# lambdaの処理に入る
def lambda_handler(event, context):

    # X-Line-Signatureからx-line-signatureに変更になったのでチェック
    if "x-line-signature" in event["headers"]:
        signature = event["headers"]["x-line-signature"]
    elif "X-Line-Signature" in event["headers"]:
        signature = event["headers"]["X-Line-Signature"]

    # 認証できなかったときのjsonを返す
    body = event["body"]
    ok_json = {"isBase64Encoded": False,
               "statusCode": 200,
               "headers": {},
               "body": ""}
    error_json = {"isBase64Encoded": False,
                  "statusCode": 403,
                  "headers": {},
                  "body": "Error"}

    if inner_date == True:
        @handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event):
            text = event.message.text
            userid = event.source.user_id
            profile = line_bot_api.get_profile(event.source.user_id)
            username = profile.display_name

        # ---------------------- メニューが選択されたときの処理 ----------------------

            if text == 'その他':
                line_bot_api.reply_message(event.reply_token, TextSendMessage(
                    text="わからないことがあれば\nreiwa2020@sawada.phys.waseda.ac.jp\nまで連絡ください"))

            elif text == "日程調整がしたい":
                buttons_template = ButtonsTemplate(
                    title='研究室見学について', text='研究室見学についての調整を行います', actions=[
                        # startというデータのpostbackeventを発行
                        PostbackAction(label='まずは登録', data='まずは登録'),
                        PostbackAction(label='日程', data='日程'),
                        PostbackAction(label='メールアドレス', data='メールアドレス'),
                        PostbackAction(label='確認', data='確認'),
                    ])
                template_message = TemplateSendMessage(
                    alt_text='Buttons alt text', template=buttons_template)
                line_bot_api.reply_message(event.reply_token, template_message)

            # メール・アドレスのときの分岐
            elif "@" in text:
                message = get_mail(text, username, userid)
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message))

            # メニュー以外に個別のメッセージが送られてきた時
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text='個別にメッセージにお答えすることができません。\n下のメニューより選択して下さい。'))

        # ---------------------- メニューが選択されたときの処理END ----------------------

        # ---------------------- 日程調整の際のボタンの選択により分岐 -------------------------

        @handler.add(PostbackEvent)
        def handle_postback(event):
            userid = event.source.user_id
            profile = line_bot_api.get_profile(event.source.user_id)
            username = profile.display_name
            data = event.postback.data

            # startが押された際の登録 裏コマンド的な
            if data == 'start':
                buttons_template = ButtonsTemplate(
                    title='My buttons sample', text='確認です。', actions=[
                        # startというデータのpostbackeventを発行
                        PostbackAction(label='start', data='start'),
                        PostbackAction(label='end', data='end'),
                        DatetimePickerAction(
                            label='show', data='show', mode="datetime"),
                        PostbackAction(label='del', data='del'),
                    ])
                template_message = TemplateSendMessage(
                    alt_text='Buttons alt text', template=buttons_template)
                line_bot_api.reply_message(event.reply_token, template_message)

            # 日程調整が押されたときの分岐
            elif data == '日程':
                with open('./date.json') as f:
                    date_message = json.load(f)
                line_bot_api.reply_message(
                    event.reply_token,
                    # alt_textがないとエラーになるので注意
                    FlexSendMessage(alt_text='訪問日', contents=date_message)
                )

            # まずは登録を押された際の分岐
            elif data == "まずは登録":
                message = create_new(username, userid)
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message))

            # 日程が押された際の分岐 dataに〜を含むのは日程のみ
            elif "~" in data:
                message = get_date(data, username, userid)
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message))

            elif data == 'メールアドレス':
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text="メール・アドレスを登録してください"))

            elif data == '確認':
                message = show_user(username, userid)
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=message))

            # ---------------------- 日程調整の際のボタンの選択により分岐END -------------------------

    # 期間外のときの処理
    elif inner_date == False:
        @handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="只今研究室見学の対象期間ではありませんので予約をすることができません。(再開: 冬頃予定)"))

    # この記述がないとhandler is not　のエラーになる
    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        logger.error("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            logger.error("  %s: %s" % (m.property, m.message))
        return error_json
    except InvalidSignatureError:
        return error_json

    return ok_json
