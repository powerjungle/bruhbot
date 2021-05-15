from toml import load, dump
import logging


async def toml_file_exists(bot, file, target, message=None):
    try:
        parsed_toml = load(file)
    except FileNotFoundError:
        open(file, 'w').close()
        if message is None:
            await bot.message(target, f"{file} doesn't exist")
        else:
            await bot.message(target, message)
        return False
    else:
        return parsed_toml


async def check_user_allowed_toml(bot, parsed_toml, target, user, message, allowed_entries, global_toml):
    if parsed_toml[global_toml][user] == {}:
        return parsed_toml

    if len(parsed_toml[global_toml][user]) >= allowed_entries:
        await bot.message(target, message)
        return False
    else:
        return parsed_toml


async def check_user_input(bot, target, length, argument, command, allow_empty_argument):
    if argument is None and allow_empty_argument is False:
        await bot.help_method(target, command)
        return False

    if len(argument) > length:
        await bot.message(target, f"too long argument, max: {length} symbols")
        return False


async def check_for_duplicates(bot, target, key, parsed_toml, global_toml, message):
    for usernames in parsed_toml[global_toml]:
        if parsed_toml[global_toml][usernames].get(key) is not None:
            logging.info(
                f"parsed_toml[{global_toml}][{usernames}].get({key}):{parsed_toml[global_toml][usernames].get(key)}"
            )
            await bot.message(target, message)
            return False

    return parsed_toml


async def check_if_any_toml(parsed_toml, if_any_what, username, toml_file):
    try:
        parsed_toml[if_any_what]
    except KeyError:
        parsed_toml[if_any_what] = {}

    try:
        parsed_toml[if_any_what][username]
    except KeyError:
        parsed_toml[if_any_what][username] = {}
        with open(toml_file, 'w') as f:
            dump(parsed_toml, f)
        return parsed_toml
    else:
        return parsed_toml
