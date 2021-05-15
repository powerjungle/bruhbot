async def alcohol_command_chars(split_arg, command_symbols):
    command_data = dict()

    for cs in command_symbols:
        command_data[cs] = 0

    for arg in split_arg:
        for cs in command_symbols:
            split_arg = arg.split(cs, maxsplit=1)
            if len(split_arg) > 1:
                try:
                    split_arg = list(filter(None, split_arg))
                    split_arg = split_arg[0]
                    command_data[cs] = split_arg
                except (IndexError, KeyError, AttributeError):
                    return False

    return command_data


async def alcohol_char_limits(command_symbols, command_data, target, bot):
    for cs in command_symbols:
        if len(str(command_data[cs])) > 5:
            await bot.message(target, "max 5 chars for alcohol arguments")
            return True
    return False


async def check_and_convert_alcohol(bot, target, command_data, command_symbols):
    for cs in command_symbols:
        try:
            command_data[cs] = float(command_data[cs])
        except ValueError:
            await bot.message(target, f"only float allowed for alcohol arguments")
            return False
    return True
