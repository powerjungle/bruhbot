from toml import load
from datetime import datetime, timedelta
from ast import literal_eval
import logging
from re import compile, search


async def get_sleeper_table(bot, target, got_username):
    try:
        parsed_toml_global_sleeper = load("sleeper_table.toml")
        sleeper_usernames = parsed_toml_global_sleeper["sleeper_usernames"]
        bot.all_hours = parsed_toml_global_sleeper["hour"]
        bot.target_sleeper = parsed_toml_global_sleeper["show_as"]
    except FileNotFoundError:
        await bot.message(target, f"the sleeper table doesn't exist")
        return False

    if got_username in sleeper_usernames:
        bot.detected_sleeper = datetime.now()


async def spam_ban(bot, got_username, target):
    try:
        buffer_size = 2
        if len(bot.last_time_buffer[got_username]) == buffer_size:
            bot.last_time_buffer[got_username].pop(0)

        bot.last_time_buffer[got_username].append(datetime.now())
    except KeyError:
        bot.last_time_buffer[got_username] = [datetime.now()]
    else:
        allowed_time_differance_seconds = 3
        calc_time_differance = 0
        for time in bot.last_time_buffer[got_username]:
            calc_time_differance = time.timestamp() - calc_time_differance
        logging.info(f"calc_time_differance: {calc_time_differance}")
        if calc_time_differance <= allowed_time_differance_seconds:
            try:
                bot.already_banned_list[got_username].append(datetime.now())
            except KeyError:
                bot.already_banned_list[got_username] = [datetime.now()]
            bot.banned_list[got_username] = datetime.now()
            detected_time_msg = \
                f"Detected {got_username} bellow allowed_time_differance_seconds: " \
                f"{allowed_time_differance_seconds}"
            logging.warning(detected_time_msg)
            await bot.message(target, f"{got_username} is spamming, ignoring messages for a bit")


async def spam_wait(bot, target, got_username):
    if bot.last_time is None:
        bot.last_time = datetime.now()
    elif datetime.now() - bot.last_time <= timedelta(
            seconds=bot.wait_time_commands):
        logging.info(f"wait time detected for: {got_username}")
        await bot.message(target, f"{got_username} less than 1 second "
                                   f"difference with last message (might not be yours)")
        return True

    bot.last_time = datetime.now()
    logging.info(f"self.last_time: {bot.last_time}")


async def recheck_banned_user(bot, got_username):
    if bot.banned_list.get(got_username):
        logging.info(f"self.banned_list[got_username]: {bot.banned_list[got_username]}")
        logging.info(
            f"self.already_banned_list[got_username]: {bot.already_banned_list[got_username]}")
        calc_wait_time = pow((bot.wait_time_list + len(bot.already_banned_list[got_username])), 2)
        logging.info(f"calc_wait_time: {calc_wait_time}")
        if datetime.now() - bot.banned_list[got_username] \
                >= timedelta(seconds=calc_wait_time):
            bot.banned_list.pop(got_username)
            logging.info(f"Removing: {got_username} from banned_list")

            if datetime.now() - bot.already_banned_list[got_username][-1] \
                    >= timedelta(seconds=calc_wait_time * 2):
                bot.already_banned_list.pop(got_username)
                logging.info(f"Removing: {got_username} from already_banned_list")
        else:
            return True


async def detect_help(bot, argument, target, second_argument=None):
    help_comm = "help"
    if help_comm in second_argument and len(second_argument[1:]) > len(help_comm):
        try:
            second_argument = second_argument[1:].split(' ', maxsplit=1)
            second_argument.remove("help")
            await bot.help_method(target, second_argument[0])
        except ValueError:
            return False
    elif argument == "help":
        await bot.help_method(target, "help")
    else:
        return False


async def check_message_config(bot, message, source, bot_name):
    if message == '':
        logging.info(f"empty message by {source}")
        return False

    bridge_name = True
    if literal_eval(str(bot.only_bridge)) is True and source != bot.bridge_bot_name:
        bridge_name = False

    if source == bot_name or 1 >= len(message) >= 256 or bridge_name is False:
        return False

    return source


async def check_regex_username(bot, message):
    try:
        regex = bot.re_pattern.search(message)
        if regex:
            bot.got_username = regex.group(1)
            bot.got_regex = regex.group(0)
            return True
        return False
    except (TypeError, AttributeError, IndexError):
        return False


async def find_command(parsed_commands, got_item):
    values = parsed_commands["command"].get(got_item)
    if values is None:
        for items in parsed_commands["command"]:
            extra = parsed_commands["command"].get(items).get("extra")
            if got_item in extra:
                values = parsed_commands["command"].get(items)
                break
        if values is None:
            return False
    return values


async def check_regex_true(string, message):
    re_compile = compile(r'' + string)
    try:
        regex = search(re_compile, message)
    except TypeError as e:
        logging.error(e)
        return False
    else:
        if regex:
            return True
        else:
            return False


async def find_regex_msg(parsed_commands, message):
    regex_result = dict()
    for reg_names in parsed_commands["regex"]:
        rx_string = parsed_commands["regex"][reg_names]["string"]
        if await check_regex_true(string=rx_string, message=message) is True:
            regex_result[reg_names] = True
    return regex_result
