import logging
from time import sleep
from telegram import *
from telegram.ext import *
import pickledb
from html import escape
import os
import sys


''' Thank you for the codes that were made available to me on GITHUB'''


# help_text = (
#     "Serves Coffee as a picture in the traditional three set"
#     "Abol, Tona, Bereka to anyone who typed buna or coffee"
#     ". By default, only the person who invited the bot into "
#     "the group is able to change settings.\nCommands:\n\n"
#     "/welcome - Set welcome message\n"
#     "/goodbye - Set goodbye message\n"
#     "/disable\\_goodbye - Disable the goodbye message\n"
#     "/lock - Only the person who invited the bot can change messages\n"
#     "/unlock - Everyone can change messages\n"
#     '/quiet - Disable "Sorry, only the person who..." '
#     "& help messages\n"
#     '/unquiet - Enable "Sorry, only the person who..." '
#     "& help messages\n\n"
#     "You can use _$username_ and _$title_ as placeholders when setting"
#     " messages. [HTML formatting]"
#     "(https://core.telegram.org/bots/api#formatting-options) "
#     "is also supported.\n"
# )


help_text = (
    "ዙሪያሽ በባህላችን የተለመደው በወሬ ጨዋታ ጊዜ የሚቀርበውን ቡና online chat ላይም እንዳይቀር "
    "ቡና የምታቀርብ bot ናት። በባህላችህንም መሰረት መጀመሪያ አቦሉን ቀጥሎም ቶናውን ከዛም በረካውን ለጠየቃት ታቀርባለች።"
    "ለማሰጀመር ቡና፣ buna ወይም coffee ብለው ጽፈው ይላኩ"
)

"""
Create database object
Database schema:
<chat_id> -> welcome message
<chat_id>_bye -> goodbye message
<chat_id>_adm -> user id of the user who invited the bot
<chat_id>_lck -> boolean if the bot is locked or unlocked
<chat_id>_quiet -> boolean if the bot is quieted
chats -> list of chat ids where the bot has received messages in.
"""

# create database object
db = pickledb.load('bot.db', True)

if not db.get("chats"):
    db.set("chats", [])

# st up logging
root = logging.getLogger()
root.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

PORT = int(os.environ.get('PORT', '8443'))


@run_async
def send_async(context, *args, **kwargs):
    context.bot.send_message(*args, **kwargs)


def check(update, context, override_lock=None):
    """
    Perform some checks on the update. If checks were successful, returns True,
    else sends an error message to the chat and returns False.
    """

    chat_id = update.message.chat_id
    chat_str = str(chat_id)

    if chat_id > 0:
        send_async(
            context, chat_id=chat_id, text="Please add me to a group first!",
        )
        return False

    locked = override_lock if override_lock is not None else db.get(chat_str + "_lck")

    if locked and db.get(chat_str + "_adm") != update.message.from_user.id:
        if not db.get(chat_str + "_quiet"):
            send_async(
                context,
                chat_id=chat_id,
                text="Sorry, only the person who invited me can do that.",
            )
        return False

    return True


# Welcome a user to the chat
def welcome(update, context, new_member):
    """ Welcomes a user to the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info(
        "%s joined to chat %d (%s)",
        escape(new_member.first_name),
        chat_id,
        escape(message.chat.title),
    )

    # Pull the custom message for this chat from the database
    text = db.get(str(chat_id))

    # Use default message if there's no custom one set
    if text is None:
        text = (f"ሰላም $username! እንኳን ወደ $title በሰላም መጣችሁ "
                "ቡና ከፈለጋችሁ ዙሪዬ 'buna' በሉኝ።")

    # Replace placeholders and send message
    text = text.replace("$username", new_member.first_name)
    text = text.replace("$title", message.chat.title)
    send_async(context, chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


# Welcome a user to the chat
def goodbye(update, context):
    """ Sends goodbye message when a user left the chat """

    message = update.message
    chat_id = message.chat.id
    logger.info(
        "%s left chat %d (%s)",
        escape(message.left_chat_member.first_name),
        chat_id,
        escape(message.chat.title),
    )

    # Pull the custom message for this chat from the database
    text = db.get(str(chat_id) + "_bye")

    # Goodbye was disabled
    if text is False:
        return
    # Use default message if there's no custom one set
    if text is None:
        text = "ቻው ቻው $username!"

    # Replace placeholders and send message
    text = text.replace("$username", message.left_chat_member.first_name)
    text = text.replace("$title", message.chat.title)
    send_async(context, chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


# Introduce the bot to a chat its been added to
def introduce(update, context):
    """
    Introduces the bot to a chat its been added to and saves the user id of the
    user who invited us.
    """

    chat_id = update.message.chat.id
    invited = update.message.from_user.id

    logger.info(
        "Invited by %s to chat %d (%s)", invited, chat_id, update.message.chat.title,
    )

    db.set(str(chat_id) + "_adm", invited)
    db.set(str(chat_id) + "_lck", True)

    text = (
        f"እሰይ እሰይ {update.message.chat.title}-ን ቡና ቤቴ አደርገዋለሁ!!!\n"
        "አሁን ቡናዬን ላፍላ ደንበኞቼም ይሰብሰቡ።"
        # "\n\nCheck the /help command for more info!"
    )
    send_async(context, chat_id=chat_id, text=text)


# print message
def buna(update, context):
    """Prints message """
    message = str(update.message.text)
    user_name = str(update.message.from_user.first_name)
    chat_id = update.effective_chat.id

    if message in ["BUNA", "coffee", "Coffee", "COFFEE", "Buna", "buna", "ቡና"]:
        buttons = [[InlineKeyboardButton(text="አዎ ጠይቂያለው", callback_data="yes")],
                   [InlineKeyboardButton(text="አልጠየኩም", callback_data="no")]]

        replay_markup = InlineKeyboardMarkup(buttons)
        context.bot.send_message(chat_id=chat_id, text=f"አንዴት ኖት {user_name}። ቡና ጠየቁኝ እንዴ?", reply_markup=replay_markup)


def buna_message(update, context):
    user_name = str(update.callback_query.from_user.first_name)
    query = update.callback_query.data
    print(query)
    if query == "yes":
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'እሺ {user_name}')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='ቡናው በአምስት ደቂቃ ይደርሳል!!!')
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='ተጫወቱ!!!')
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open('img10.jpg', 'rb'))

        sleep(120)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open('img1.jpg', 'rb'))
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"አቦሉ ደርሷል {user_name}!!")
        sleep(120)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open('img2.jpg', 'rb'))
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"ቶናው ደርሷል {user_name}!!")
        sleep(120)
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=open('img5.jpg', 'rb'))
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"በረካው ደርሷል {user_name}!!")
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="ተጫወቱ!!!")

    elif query == "no":
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="እሺ ተጫወቱ።")


# Print help text
def help(update, context):
    """ Prints help text """

    chat_id = update.message.chat.id
    chat_str = str(chat_id)
    if (
        not db.get(chat_str + "_quiet")
        or db.get(chat_str + "_adm") == update.message.from_user.id
    ):
        send_async(
            context,
            chat_id=chat_id,
            text=help_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )


# Set custom message
def set_welcome(update, context):
    """ Sets custom welcome message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context):
        return

    # Split message into words and remove mentions of the bot
    message = update.message.text.partition(" ")[2]

    # Only continue if there's a message
    if not message:
        send_async(
            context,
            chat_id=chat_id,
            text="You need to send a message, too! For example:\n"
            "<code>/welcome Hello $username, welcome to "
            "$title!</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Put message into database
    db.set(str(chat_id), message)

    send_async(context, chat_id=chat_id, text="Got it!")


# Set custom message
def set_goodbye(update, context):
    """ Enables and sets custom goodbye message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context):
        return

    # Split message into words and remove mentions of the bot
    message = update.message.text.partition(" ")[2]

    # Only continue if there's a message
    if not message:
        send_async(
            context,
            chat_id=chat_id,
            text="You need to send a message, too! For example:\n"
            "<code>/goodbye Goodbye, $username!</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Put message into database
    db.set(str(chat_id) + "_bye", message)

    send_async(context, chat_id=chat_id, text="Got it!")


def disable_goodbye(update, context):
    """ Disables the goodbye message """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context):
        return

    # Disable goodbye message
    db.set(str(chat_id) + "_bye", False)

    send_async(context, chat_id=chat_id, text="Got it!")


def lock(update, context):
    """ Locks the chat, so only the invitee can change settings """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + "_lck", True)

    send_async(context, chat_id=chat_id, text="Got it!")


def quiet(update, context):
    """ Quiets the chat, so no error messages will be sent """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + "_quiet", True)

    send_async(context, chat_id=chat_id, text="Got it!")


def unquiet(update, context):
    """ Unquiets the chat """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context, override_lock=True):
        return

    # Lock the bot for this chat
    db.set(str(chat_id) + "_quiet", False)

    send_async(context, chat_id=chat_id, text="Got it!")


def unlock(update, context):
    """ Unlocks the chat, so everyone can change settings """

    chat_id = update.message.chat.id

    # Check admin privilege and group context
    if not check(update, context):
        return

    # Unlock the bot for this chat
    db.set(str(chat_id) + "_lck", False)

    send_async(context, chat_id=chat_id, text="Got it!")


def empty_message(update, context):
    """
    Empty messages could be status messages, so we check them if there is a new
    group member, someone left the chat or if the bot has been added somewhere.
    """

    # Keep chatlist
    chats = db.get("chats")

    if update.message.chat.id not in chats:
        chats.append(update.message.chat.id)
        db.set("chats", chats)
        logger.info("I have been added to %d chats" % len(chats))

    if update.message.new_chat_members:
        for new_member in update.message.new_chat_members:
            # Bot was added to a group chat
            if new_member.username == 'zuriashbunabot':
                return introduce(update, context)
            # Another user joined the chat
            else:
                return welcome(update, context, new_member)

    # Someone left the chat
    elif update.message.left_chat_member is not None:
        if update.message.left_chat_member.username != 'zuriashbunabot':
            return goodbye(update, context)


# error handling
def error(update, context, **kwargs):
    """Error handling"""
    error = context.error

    try:
        if isinstance(error, TelegramError) and (
            error.message == 'Unauthorized'
            or error.message == "Have no right to send message"
            or "PEER_ID_INVALID" in error.message
        ):
            chats = db.get('chats')
            chats.remove(update.message.chat_id)
            db.set("chats", chats)
            logger.info("Removed chat_id %s from chat list" % update.message.chat_id)

        else:
            logger.error("An error (%s) occurred: %s" % (type(error), error.message))
    except:
        pass


# All operates from there
def main():
    updater = Updater('1457319887:AAELoLlfXeTkEy7J15ywP8I_E2YSBtKORJ4')
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", help))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CallbackQueryHandler(buna_message))
    dp.add_handler(CommandHandler("welcome", set_welcome))
    dp.add_handler(CommandHandler("goodbye", set_goodbye))
    dp.add_handler(CommandHandler("disable_goodbye", disable_goodbye))
    dp.add_handler(CommandHandler("lock", lock))
    dp.add_handler(CommandHandler("unlock", unlock))
    dp.add_handler(CommandHandler("quiet", quiet))
    dp.add_handler(CommandHandler("unquiet", unquiet))

    dp.add_handler(MessageHandler(Filters.text, buna))
    dp.add_handler(MessageHandler(Filters.status_update, empty_message))

    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path='1457319887:AAELoLlfXeTkEy7J15ywP8I_E2YSBtKORJ4')
    # updater.bot.set_webhook(url=settings.WEBHOOK_URL)
    updater.bot.set_webhook("https://zuriashbunabot.herokuapp.com/" + '1457319887:AAELoLlfXeTkEy7J15ywP8I_E2YSBtKORJ4')


    updater.idle()


if __name__ == '__main__':
    main()