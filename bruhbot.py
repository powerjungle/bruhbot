import pydle
import toml
import re
import datetime
import logging
from ast import literal_eval

from bruhbot_ping_methods import ping_filtered, connection_to_host
from bruhbot_toml_checks import toml_file_exists, check_user_allowed_toml, \
    check_user_input, check_for_duplicates
from bruhbot_alcohol_methods import alcohol_command_chars, alcohol_char_limits, check_and_convert_alcohol
from bruhbot_on_message_detection import get_sleeper_table, spam_ban, spam_wait, \
    recheck_banned_user, detect_help, check_message_config, check_regex_username, find_command, find_regex_msg

parsed_toml_global = toml.load("bot-config.toml")
bot_name = parsed_toml_global["bot_name"]
tls = parsed_toml_global["tls"]
tls_verify = parsed_toml_global["tls_verify"]
password = parsed_toml_global["password"]
host = parsed_toml_global["host"]
port = int(parsed_toml_global["port"])
sasl_identify = parsed_toml_global["sasl_identify"]

try:
    parsed_commands = toml.load("local-commands.toml")
except FileNotFoundError:
    parsed_commands = toml.load("commands.toml")

comm_char = parsed_commands["command_char"]

if not literal_eval(str(sasl_identify)):
    sasl_username = None
    sasl_password = None
    sasl_mechanism = None
else:
    sasl_username = parsed_toml_global["sasl_username"]
    sasl_password = parsed_toml_global["sasl_password"]
    sasl_mechanism = parsed_toml_global["sasl_mechanism"]

logging.basicConfig(level=logging.INFO)


async def append_to_toml(file, key, value, global_value, global_subvalue, just_change=False):
    reload_whole_toml = toml.load(file)

    global_stuff = reload_whole_toml[global_value][global_subvalue]

    if just_change is False:
        if_state = key not in global_stuff
    else:
        if_state = key in global_stuff

    if if_state:
        global_stuff[key] = value
        with open(file, 'w') as f:
            toml.dump(reload_whole_toml, f)
        return True
    else:
        return False


async def remove_from_toml(file, key, global_value, global_subvalue):
    reload_whole_toml = toml.load(file)

    global_stuff = reload_whole_toml[global_value][global_subvalue]

    if key in global_stuff:
        global_stuff.pop(key)
        with open(file, 'w') as f:
            toml.dump(reload_whole_toml, f)
        return True
    else:
        return False


class MyOwnBot(pydle.Client):
    bridge_regex = None
    bridge_bot_name = None
    use_regex = None
    got_username = None
    got_regex = None
    only_bridge = None
    debug = None
    re_pattern = re.compile(r'')
    target_sleeper = None
    all_hours = None

    detected_sleeper = None

    last_time = None
    last_time_buffer = dict()

    wait_time_commands = 1
    wait_time_list = 2

    banned_list = dict()
    already_banned_list = dict()

    ideas_file_name = "ideas_store.toml"
    no_ideas_message = "no ideas"
    idea_toml_global = "ideas"
    ideas_toml_limit = 5

    max_entr_msg = " has reached the limit of "

    title_limit = 20
    description_limit = 150

    async def on_connect(self):
        parsed_toml = toml.load("bot-config.toml")
        self.use_regex = parsed_toml["use_bridge_regex"]
        if literal_eval(str(self.use_regex)) is True:
            self.bridge_regex = parsed_toml["bridge_regex"]
            self.bridge_bot_name = parsed_toml["bridge_bot_name"]
            self.only_bridge = parsed_toml["only_bridge"]
            self.debug = parsed_toml["debug"]
            self.re_pattern = re.compile(r'' + self.bridge_regex)

        channel = parsed_toml["channel"]
        await self.join(channel)

    async def help_method(self, target, argument):
        for_help_format = ""

        values = False
        if argument != "help":
            values = await find_command(parsed_commands, argument)
        if values is False:
            for items in parsed_commands["command"]:
                ext_str = ''
                for xtr in parsed_commands["command"].get(items).get("extra"):
                    ext_str += f" / {xtr}"
                for_help_format += f" || {items}"
                for_help_format += ext_str
        else:
            got_help = values.get("help_txt")
            for_help_format = f"{argument}: {got_help}"

        await self.message(target, for_help_format)

    async def ping_me(self, target, argument):
        get_port = argument.split(':', maxsplit=1)
        get_port.pop(0)
        get_port = get_port[0].split(' ', maxsplit=1)

        try:
            get_port = get_port[1].split(':', maxsplit=1)
        except IndexError:
            await self.message(target, "pong")
            return
        logging.info(get_port)
        if len(get_port) == 2:
            hostname = get_port[0]
            argument_port = get_port[1]
            got_port = argument_port
            if not got_port.isdigit():
                try:
                    ping_config = toml.load("ping_config.toml")
                    try:
                        got_port = ping_config["port"].get(got_port).get("number")
                    except AttributeError:
                        await self.message(target, f"unknown port: {got_port}")
                        return
                except FileNotFoundError:
                    await self.message(target, "no pings configured")

        elif len(get_port) == 1:
            hostname = get_port[0]
            argument_port = 80
            got_port = argument_port
        else:
            return

        unknown_port_msg = f"{argument} UNKNOWN"

        ping_filter_result = await ping_filtered(self, hostname, target, unknown_port_msg)
        if ping_filter_result is True:
            return

        print_hostname = f"{hostname}:{argument_port}"

        conn_to_host_result = await connection_to_host(self, target, hostname,
                                                       unknown_port_msg, got_port, print_hostname)
        if conn_to_host_result is False:
            return

    async def ping_ports(self, target, argument=None):
        format_string = ''
        ping_config = toml.load("ping_config.toml")
        for name in ping_config["port"]:
            format_string += f"{name}, "
        await self.message(target, format_string)

    async def add_idea(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_username = split_arg[0]
        arg_argument = split_arg[1]

        try:
            arg_argument = arg_argument.split(' ', maxsplit=1)
            split_arg2 = arg_argument[1].split('-', maxsplit=1)
        except IndexError:
            return

        just_change = False

        limit = self.title_limit
        argument = split_arg2[0]
        key = argument
        bypass_uac = False
        bypass_cfd = False
        if len(split_arg2) > 1:
            limit = self.description_limit
            argument = split_arg2[1]
            key = split_arg2[0]
            just_change = True
            bypass_uac = True
            bypass_cfd = True

        max_entr_msg = f"{arg_username}{self.max_entr_msg}{str(self.ideas_toml_limit)} ideas"
        duplicates_message = f"{argument} already exists"

        ideas_file_toml = toml.load(self.ideas_file_name)

        toml_file_exists_result = await toml_file_exists(self, self.ideas_file_name, target)
        if toml_file_exists_result is False:
            return

        check_user_input_result = await check_user_input(self, target, limit, argument,
                                                         "help", allow_empty_argument=False)
        if check_user_input_result is False:
            return

        if bypass_cfd is False:
            check_user_allowed_toml_result = await check_user_allowed_toml(self,
                                                                           ideas_file_toml, target, arg_username,
                                                                           max_entr_msg, self.ideas_toml_limit,
                                                                           self.idea_toml_global)
            if check_user_allowed_toml_result is False:
                return

        if bypass_uac is False:
            check_for_duplicates_result = await check_for_duplicates(self, target, key, ideas_file_toml,
                                                                     self.idea_toml_global, duplicates_message)
            if check_for_duplicates_result is False:
                return

        append_result = await append_to_toml(file=self.ideas_file_name, key=key, value=argument,
                                             global_value=self.idea_toml_global, global_subvalue=arg_username,
                                             just_change=just_change)
        if append_result is False:
            if just_change is False:
                await self.message(target, f"this name is taken, use '~ri title' to "
                                           f"remove it (this will remove the idea as well) or"
                                           f" '~aia title-description' to change the description")
            if just_change is True:
                await self.message(target, f"there's no such title, use '~aia title' to create it")
            return

        await self.message(target, f"the ideas are updated")

    async def remove_idea(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_username = split_arg[0]
        arg_argument = split_arg[1]

        try:
            arg_argument = arg_argument.split(' ', maxsplit=1)[1]
        except IndexError:
            return

        toml_file_exists_result = await toml_file_exists(self, self.ideas_file_name, target, message=None)
        if toml_file_exists_result is False:
            return

        remove_result = await remove_from_toml(file=self.ideas_file_name, key=arg_argument,
                                               global_value=self.idea_toml_global, global_subvalue=arg_username)
        if remove_result is False:
            await self.message(target, f"either the idea doesn't exist '{arg_argument}' or you aren't the author")
        else:
            await self.message(target, f"the idea '{arg_argument}' is removed successfully")

    async def ideas_match_usernames(self, check_result):
        ideas_intro = "Ideas"
        format_message = ideas_intro
        for usernames in check_result[self.idea_toml_global]:
            if check_result[self.idea_toml_global][usernames] != {}:
                format_message += f" || by <{usernames}>: "
            for idea_titles in check_result[self.idea_toml_global][usernames]:
                format_message += f"{idea_titles}, "
            if format_message != ideas_intro:
                format_message = format_message[:len(format_message) - 2]
        return format_message

    async def ideas(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_argument = split_arg[1]

        second_split = arg_argument.split(' ', maxsplit=1)

        toml_file_exists_result = await toml_file_exists(self, self.ideas_file_name, target, message=None)
        if toml_file_exists_result is False:
            return

        check_result = toml_file_exists_result

        if len(second_split) == 1:
            format_message = await self.ideas_match_usernames(check_result)
            await self.message(target, format_message)
            return

        got_idea_detail = None
        got_idea_username = None
        for usernames in check_result[self.idea_toml_global]:
            try:
                got_idea_detail = check_result[self.idea_toml_global].get(usernames).get(second_split[1])
                got_idea_username = usernames
            except KeyError:
                pass

            if got_idea_detail is not None:
                break

        if got_idea_detail == '':
            await self.message(target, f"empty idea, use '~aia {second_split[1]}-description'"
                                       f" if you have written the title")
            return

        if got_idea_detail is None:
            await self.message(target, f"the idea doesn't exist: {second_split[1]}")
            return

        await self.message(target,
                           f"idea: {second_split[1]}; by: <{got_idea_username}>: {got_idea_detail}")

    async def alcohol(self, target, argument):
        split_arg = argument.split(' ', maxsplit=3)
        if argument is None or len(split_arg) < 2:
            await self.help_method(target, "alcohol")
            return

        split_arg[0] = split_arg[0].split(':', maxsplit=1)[1]
        split_arg[0] = split_arg[0][1:]

        command_symbols = ["ml", "%", "perct", "unitst", "milit"]

        command_data = await alcohol_command_chars(split_arg, command_symbols)

        char_limit_result = await alcohol_char_limits(command_symbols, command_data, target, self)
        if char_limit_result is True:
            return

        check_and_convert_alcohol_result = await check_and_convert_alcohol(self, target, command_data, command_symbols)
        if check_and_convert_alcohol_result is False:
            return

        logging.info(command_data)

        extra_info = ''

        arg_ml = command_data[command_symbols[0]]
        arg_percent = command_data[command_symbols[1]]

        if arg_ml == 0 or arg_percent == 0:
            await self.message(target, "ml/% can't be 0/empty")
            return

        arg_target_percent = command_data[command_symbols[2]]
        arg_unit_target = command_data[command_symbols[3]]
        arg_target_ml = command_data[command_symbols[4]]
        final_result = round((arg_ml * (arg_percent / 100)) / 10, 2)

        if arg_unit_target != 0:
            final_target_units_ml = int((arg_unit_target * 10) / (arg_percent / 100))
            final_remove_amount = arg_ml - final_target_units_ml
            extra_info += f"; for {arg_unit_target} units (UK), " \
                          f"it must become {final_target_units_ml}ml at {arg_percent}% " \
                          f"or must remove {final_remove_amount}ml from the total amount"
        elif arg_target_percent != 0:
            final_target_percent = int((arg_percent / arg_target_percent) * arg_ml - arg_ml)
            final_target_percent_all = int(final_target_percent + arg_ml)
            extra_info += f"; add: {final_target_percent}ml water " \
                          f"(total {final_target_percent_all}ml) for {arg_target_percent}%"
        elif arg_target_ml != 0:
            final_target_ml_water = int((arg_ml / arg_target_ml) * arg_percent)
            final_target_ml_same = round((arg_target_ml * (arg_percent / 100)) / 10, 2)
            if arg_target_ml > arg_ml:
                arg_diff = arg_target_ml - arg_ml
                units_diff = final_target_ml_same - final_result
                extra_info += f"; for target: {arg_target_ml}ml, if water is added {arg_diff}ml, it becomes: " \
                              f"{final_target_ml_water}%, if alcohol is added with the same percentage {arg_diff}" \
                              f"ml, it becomes: {final_target_ml_same} units ({units_diff} units more)"
            elif arg_target_ml < arg_ml:
                arg_diff = arg_ml - arg_target_ml
                units_diff = final_result - final_target_ml_same
                extra_info += f"; for target: {arg_target_ml}ml, if water is removed {arg_diff}ml, it becomes: " \
                              f"{final_target_ml_water}%, if alcohol is removed with the same percentage " \
                              f"{arg_diff}ml, it becomes: {final_target_ml_same} units ({units_diff} units less)"
            elif arg_target_ml == arg_ml:
                extra_info += f"; target: {arg_target_ml}ml is the same as the original ml"

        await self.message(target, f"for {arg_ml}ml {arg_percent}%: {final_result} units (UK){extra_info}")

    async def target_sleeps(self, target, argument=None):
        now = datetime.datetime.now()
        extra_msg = ''

        got_percent = self.all_hours[str(now.hour)].get("percent")
        if now.hour + 1 == 24:
            now_hour = "0"
        else:
            now_hour = str(now.hour + 1)
        got_next_percent = self.all_hours[now_hour].get("percent")
        # logging.info(f"got_next_percent: {got_next_percent}")

        # logging.info(f"got_now_minute: {now.minute}")

        now_minutes_percent = now.minute / 60
        # logging.info(f"now_minutes_percent: {now_minutes_percent}")

        percent_diff = got_percent - got_next_percent
        # logging.info(f"percent_diff: {percent_diff}")
        final_diff = now_minutes_percent * percent_diff
        # logging.info(f"final_diff: {final_diff}")
        final_percent = got_percent - final_diff
        # logging.info(f"final_percent: {final_percent}")

        if self.detected_sleeper is not None:
            sleeper_detect_diff = now - self.detected_sleeper
        else:
            sleeper_detect_diff = datetime.timedelta(hours=12)

        calc_time = 120 - ((int(final_percent) / 100) * 120)
        wait_time = round(calc_time)
        logging.info(f"Final percent: {final_percent} Wait time: {wait_time}")

        if sleeper_detect_diff <= datetime.timedelta(minutes=wait_time) and final_percent != 1.0:
            calc_percent_of = (sleeper_detect_diff.seconds / 60) / wait_time
            logging.info(f"calc_percent_of:{calc_percent_of}")
            final_percent = final_percent * calc_percent_of
            logging.info(f"final_percent:{final_percent}")
            if final_percent < 1.0:
                final_percent = 1.0
            detected_minutes = self.detected_sleeper.minute
            if len(str(detected_minutes)) < 2:
                detected_minutes = '0' + str(detected_minutes)
            extra_msg = f"({self.target_sleeper} has sent a message: {self.detected_sleeper.hour}:{detected_minutes})"

        await self.message(target, f"chance {self.target_sleeper} to sleep now: {round(final_percent, 2)}% {extra_msg}")

    async def mix_alcohol(self, target, argument=None):
        await self.message(target, "mix alcohol info: https://pastebin.com/raw/9LZCqNg0 ; "
                                   "links: https://imgur.com/a/vzaiwSN (layering demo) ; "
                                   "https://www.goodcocktails.com/bartending/specific_gravity.php (specific gravity)")

    async def regex_six_nine(self, target):
        await self.message(target, "nice")

    async def on_message(self, target, source, message):
        logging.info(f"source: {source}")
        logging.info(f"message: {message}")

        check_message_config_result = await check_message_config(self, message, source, bot_name)
        if check_message_config_result is False:
            return

        got_username = check_message_config_result

        regex = await check_regex_username(self, message)
        if regex is True:
            got_username = self.got_username

        if regex is True:
            message = message.replace(self.got_regex, '')

        if not message.startswith(comm_char):
            return

        get_sleeper_result = await get_sleeper_table(self, target, got_username)
        if get_sleeper_result is False:
            return

        recheck_banned_user_result = await recheck_banned_user(self, got_username)
        if recheck_banned_user_result is True:
            return

        regex_result = await find_regex_msg(parsed_commands, message)

        # logging.info(f"regex_result: {regex_result}")

        spam_wait_result = await spam_wait(self, target, got_username)
        if spam_wait_result is True:
            return

        await spam_ban(self, got_username, target)

        logging.info(f"detected message: {message} by {got_username}")
        if target == bot_name:
            logging.info(f"messages is pm by {got_username}, setting target")
            target = got_username

        whole_message = message
        got_item = message[1:].split(' ', maxsplit=1)
        got_item = got_item[0]

        detect_help_result = await detect_help(self, got_item, target, whole_message)
        if detect_help_result is not False:
            return

        values = await find_command(parsed_commands, got_item)
        if values is False:
            await self.message(target, f"there's no such command: {got_item}")
            return

        method = values.get("method")

        await getattr(self, str(method))(target, f"{got_username}:{whole_message}")

        for rx in regex_result:
            method = parsed_commands["regex"].get(rx).get("method")
            if method:
                await getattr(self, str(method))(target)


client = MyOwnBot(nickname=bot_name,
                  realname="Bruh Bot",
                  sasl_username=sasl_username,
                  sasl_password=sasl_password,
                  sasl_mechanism=sasl_mechanism)
client.RECONNECT_MAX_ATTEMPTS = 6
client.run(hostname=host, port=port, tls=literal_eval(str(tls)),
           tls_verify=literal_eval(str(tls_verify)), password=password)
