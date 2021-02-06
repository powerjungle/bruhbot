import pydle
import toml
import re
import datetime
import logging
import socket

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

if not sasl_identify:
    sasl_username = None
    sasl_password = None
    sasl_mechanism = None
else:
    sasl_username = parsed_toml_global["sasl_username"]
    sasl_password = parsed_toml_global["sasl_password"]
    sasl_mechanism = parsed_toml_global["sasl_mechanism"]

logging.basicConfig(level=logging.INFO)


async def check_regex_true(string, message):
    try:
        regex = re.search(r'' + string, message)
    except TypeError as e:
        logging.error(e)
        return False
    else:
        if regex:
            return True
        else:
            return False


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
            toml.dump(parsed_toml, f)
        return parsed_toml
    else:
        return parsed_toml


class MyOwnBot(pydle.Client):
    bridge_regex = None
    bridge_bot_name = None
    use_regex = None
    got_username = None
    got_regex = None
    only_bridge = None
    debug = None
    repattern = None
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
        if self.use_regex is True:
            self.bridge_regex = parsed_toml["bridge_regex"]
            self.bridge_bot_name = parsed_toml["bridge_bot_name"]
            self.only_bridge = parsed_toml["only_bridge"]
            self.debug = parsed_toml["debug"]
            self.repattern = re.compile(r'' + self.bridge_regex)

        channel = parsed_toml["channel"]
        await self.join(channel)

    async def check_regex_username(self, message):
        try:
            regex = self.repattern.search(message)
        except TypeError as e:
            logging.error(e)
            return False
        else:
            if regex:
                # logging.info("regex found pattern")
                self.got_username = regex.group(1)
                self.got_regex = regex.group(0)
                return True
            else:
                # logging.info("regex didn't find patter")
                return False

    async def help_method(self, target, argument):
        for_help_format = ""

        for item in parsed_commands.get("command"):
            values = parsed_commands["command"].get(item)
            extra = values.get("extra")
            if argument == item or argument in extra:
                got_help = values.get("help_txt")
                for_help_format = ""
                for_help_format += f"{argument}: {got_help}"
                break
            else:
                ext_str = ''
                for xtr in extra:
                    ext_str += f"{xtr}/"
                for_help_format += f"| {item}/{ext_str} "

        await self.message(target, for_help_format)

    async def pingme(self, target, argument):
        if argument is None:
            await self.message(target, "pong")
        else:
            get_port = argument.split(':')
            if len(get_port) == 2:
                hostname = get_port[0]
                argument_port = get_port[1]
                port = argument_port
                if not port.isdigit():
                    try:
                        ping_config = toml.load("ping_config.toml")
                    except FileNotFoundError:
                        await self.message(target, "no pings configured")
                    else:
                        try:
                            port = ping_config["port"].get(port).get("number")
                        except AttributeError:
                            await self.message(target, f"unknown port: {port}")
                            return
            elif len(get_port) == 1:
                hostname = get_port[0]
                argument_port = 80
                port = argument_port
            else:
                return

            unknown_port_msg = f"{argument} UNKNOWN"

            try:
                regex = re.search(r'192\.168.*', hostname)
            except TypeError:
                await self.message(target, unknown_port_msg)
            else:
                if regex:
                    await self.message(target, unknown_port_msg)
                    return

            if hostname == "localhost":
                await self.message(target, unknown_port_msg)
                return

            if hostname == "127.0.0.1":
                await self.message(target, unknown_port_msg)
                return

            print_hostname = f"{hostname}:{argument_port}"

            try:
                got_host = socket.gethostbyname(hostname)
            except socket.gaierror:
                await self.message(target, unknown_port_msg)
                return

            try:
                s = socket.create_connection(address=(got_host, port), timeout=3)
            except OSError:
                await self.message(target, f"{print_hostname} DOWN")
            else:
                s.close()
                await self.message(target, f"{print_hostname} UP")

    async def ping_ports(self, target):
        format_string = ''
        ping_config = toml.load("ping_config.toml")
        for name in ping_config["port"]:
            format_string += f"{name}, "
        await self.message(target, format_string)

    async def toml_file_exists(self, file, target, message):
        try:
            parsed_toml = toml.load(file)
        except FileNotFoundError:
            open(file, 'w').close()
            await self.message(target, message)
            return False
        else:
            return parsed_toml

    async def check_user_allowed_toml(self,
                                      parsed_toml,
                                      target,
                                      user,
                                      message,
                                      allowed_entries,
                                      global_toml,
                                      bypass_check=False):
        if bypass_check is True:
            return parsed_toml

        if parsed_toml[global_toml][user] == {}:
            return parsed_toml

        if len(parsed_toml[global_toml][user]) >= allowed_entries:
            await self.message(target, message)
            return False
        else:
            return parsed_toml

    async def check_user_input(self, target, length, argument, command, allow_empty_argument):
        if argument == "None" and allow_empty_argument is False:
            await self.help_method(target, command)
            return False

        if len(argument) > length:
            await self.message(target, f"too long argument, max: {length} symbols")
            return False

    async def check_for_duplicates(self,
                                   target,
                                   key,
                                   parsed_toml,
                                   global_toml,
                                   message,
                                   bypass_check=False):
        if bypass_check is True:
            return parsed_toml

        for usernames in parsed_toml[global_toml]:
            if parsed_toml[global_toml][usernames].get(key) is not None:
                logging.info(f"parsed_toml[{global_toml}][{usernames}].get({key}):{parsed_toml[global_toml][usernames].get(key)}")
                await self.message(target, message)
                return False

        return parsed_toml

    async def for_toml_full_check(self,
                                  target,
                                  argument,
                                  username,
                                  toml_file,
                                  if_any,
                                  toml_exist_message,
                                  limit,
                                  duplicates_message=None,
                                  max_entr_msg=None,
                                  entries_limit=999,
                                  bypass_user_allow_check=False,
                                  bypass_check_for_duplicates=False,
                                  command=None,
                                  allow_empty_argument=False):
        user_input_result = await self.check_user_input(target=target,
                                                        length=limit,
                                                        argument=argument,
                                                        command=command,
                                                        allow_empty_argument=allow_empty_argument)
        if user_input_result is False:
            return False

        ideas_parsed_toml = await self.toml_file_exists(file=toml_file,
                                                        target=target,
                                                        message=toml_exist_message)

        if ideas_parsed_toml is not False:
            if_any_ideas = await check_if_any_toml(parsed_toml=ideas_parsed_toml,
                                                   if_any_what=if_any,
                                                   username=username,
                                                   toml_file=toml_file)
            if if_any_ideas is not False:
                if_allowed_user = await self.check_user_allowed_toml(parsed_toml=if_any_ideas,
                                                                     target=target,
                                                                     user=username,
                                                                     message=max_entr_msg,
                                                                     allowed_entries=entries_limit,
                                                                     bypass_check=bypass_user_allow_check,
                                                                     global_toml=if_any)

                if if_allowed_user is not False:
                    if_duplicates = await self.check_for_duplicates(target=target,
                                                                    key=argument,
                                                                    parsed_toml=if_allowed_user,
                                                                    global_toml=if_any,
                                                                    message=duplicates_message,
                                                                    bypass_check=bypass_check_for_duplicates)
                    if if_duplicates is not False:
                        return if_duplicates

        return False

    async def add_idea(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_username = split_arg[0]
        arg_argument = split_arg[1]

        value = ''
        just_change = False
        entries_limit = self.ideas_toml_limit

        split_arg2 = arg_argument.split('-', maxsplit=1)
        if len(split_arg2) > 1:
            limit = self.description_limit
            argument = split_arg2[1]
            key = split_arg2[0]
            value = argument
            just_change = True
            bypass_uac = True
            bypass_cfd = True
        else:
            limit = self.title_limit
            argument = split_arg2[0]
            key = argument
            bypass_uac = False
            bypass_cfd = False

        max_entr_msg = f"{arg_username}{self.max_entr_msg}{str(self.ideas_toml_limit)} ideas"

        duplicates_message = f"{argument} already exists"

        check_result = await self.for_toml_full_check(target=target,
                                                      argument=argument,
                                                      username=arg_username,
                                                      limit=limit,
                                                      toml_file=self.ideas_file_name,
                                                      if_any=self.idea_toml_global,
                                                      toml_exist_message=self.no_ideas_message,
                                                      max_entr_msg=max_entr_msg,
                                                      entries_limit=entries_limit,
                                                      duplicates_message=duplicates_message,
                                                      bypass_user_allow_check=bypass_uac,
                                                      bypass_check_for_duplicates=bypass_cfd,
                                                      command="add_idea")

        if check_result is not False:
            append_result = await append_to_toml(file=self.ideas_file_name, key=key, value=value,
                                                 global_value=self.idea_toml_global, global_subvalue=arg_username,
                                                 just_change=just_change)
            if append_result is False:
                if just_change is False:
                    await self.message(target, f"this name is taken, use '~ri title' to "
                                               f"remove it (this will remove the idea as well) or"
                                               f" '~aia title-description' to change the description")
                if just_change is True:
                    await self.message(target, f"there's no such title, use '~aia title' to create it")
            else:
                await self.message(target, f"the ideas are updated")

    async def remove_idea(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_username = split_arg[0]
        arg_argument = split_arg[1]

        limit = self.title_limit
        check_result = await self.for_toml_full_check(target=target,
                                                      argument=arg_argument,
                                                      username=arg_username,
                                                      limit=limit,
                                                      toml_file=self.ideas_file_name,
                                                      if_any=self.idea_toml_global,
                                                      toml_exist_message=self.no_ideas_message,
                                                      bypass_user_allow_check=True,
                                                      bypass_check_for_duplicates=True,
                                                      command="remove_idea")

        if check_result is not False:
            remove_result = await remove_from_toml(file=self.ideas_file_name, key=arg_argument,
                                                   global_value=self.idea_toml_global, global_subvalue=arg_username)
            if remove_result is False:
                await self.message(target, f"either the idea doesn't exist '{arg_argument}' or you aren't the author")
            else:
                await self.message(target, f"the idea '{arg_argument}' is removed successfully")

    async def ideas(self, target, argument):
        split_arg = argument.split(':', maxsplit=1)
        arg_username = split_arg[0]
        arg_argument = split_arg[1]
        if arg_argument == "None":
            arg_argument = "just_continue"
            argument = None

        limit = self.title_limit
        check_result = await self.for_toml_full_check(target=target,
                                                      argument=arg_argument,
                                                      username=arg_username,
                                                      limit=limit,
                                                      toml_file=self.ideas_file_name,
                                                      if_any=self.idea_toml_global,
                                                      toml_exist_message=self.no_ideas_message,
                                                      bypass_user_allow_check=True,
                                                      bypass_check_for_duplicates=True,
                                                      allow_empty_argument=True)
        if check_result is not False:
            if argument is None:
                format_message = ''
                format_message += "Ideas"
                for usernames in check_result[self.idea_toml_global]:
                    if check_result[self.idea_toml_global][usernames] != {}:
                        format_message += f";by <{usernames}>: "
                    for idea_titles in check_result[self.idea_toml_global][usernames]:
                        format_message += f"{idea_titles}, "
                await self.message(target, format_message)
            else:
                got_idea_detail = None
                got_idea_username = None
                for usernames in check_result[self.idea_toml_global]:
                    try:
                        got_idea_detail = check_result[self.idea_toml_global][usernames][arg_argument]
                    except KeyError:
                        pass
                    else:
                        got_idea_username = usernames
                        break
                if got_idea_detail is not None:
                    if got_idea_detail != '':
                        await self.message(target, f"idea: {arg_argument}; by: <{got_idea_username}>: {got_idea_detail}")
                    else:
                        await self.message(target, f"empty idea, use '~aia {arg_argument}-description'"
                                                   f" if you have written the title")
                else:
                    await self.message(target, f"the idea doesn't exist: {arg_argument}")

    async def check_and_convert_alcohol(self, target, ml, percent, target_percent, units, target_ml):
        try:
            arg_ml = int(ml)
            arg_percent = float(percent)
            arg_target_percent = float(target_percent)
            arg_units = float(units)
            target_ml = int(target_ml)
        except ValueError:
            await self.message(target, f"only digits for ml (whole numbers) and percent/units (fractions)")
            return False
        else:
            return [arg_ml, arg_percent, arg_target_percent, arg_units, target_ml]

    async def alcohol(self, target, argument):
        if argument is None:
            await self.help_method(target, "alcohol")
            return

        split_arg = argument.split(' ', maxsplit=2)
        if len(split_arg) < 2:
            await self.help_method(target, "alcohol")
            return

        arg_ml = '0'
        arg_percent = '0'
        arg_unit_target = '0'
        arg_target_percent = '0'
        arg_target_ml = '0'

        command_symbols = ["ml", '%', "unitst", "%=", "mlt"]

        for command in command_symbols:
            for arg in split_arg:
                if arg.endswith(command):
                    got_value = arg.replace(command, '')
                    if command == command_symbols[0]:
                        arg_ml = got_value
                    elif command == command_symbols[1]:
                        arg_percent = got_value
                    elif command == command_symbols[2]:
                        arg_unit_target = got_value
                    elif command == command_symbols[3]:
                        arg_target_percent = got_value
                    elif command == command_symbols[4]:
                        arg_target_ml = got_value

        if len(arg_ml) > 5 or \
                len(arg_target_ml) > 5 or \
                len(arg_percent) > 6 or \
                len(arg_target_percent) > 6 or \
                len(arg_unit_target) > 2:
            await self.message(target, "max 5 chars for ml, 6 for percents, and 2 for units")
            return

        got_result = await self.check_and_convert_alcohol(target,
                                                          arg_ml,
                                                          arg_percent,
                                                          arg_target_percent,
                                                          arg_unit_target,
                                                          arg_target_ml)
        if got_result is not False:
            extra_info = ''

            arg_ml = got_result[0]
            arg_percent = got_result[1]

            if arg_ml == 0 or arg_percent == 0:
                await self.message(target, "ml/% can't be 0/empty")
                return

            arg_target_percent = got_result[2]
            arg_unit_target = got_result[3]
            arg_target_ml = got_result[4]
            final_result = round((arg_ml * (arg_percent/100))/10, 2)

            if arg_unit_target != 0:
                final_target_units_ml = int((arg_unit_target*10)/(arg_percent/100))
                final_remove_amount = arg_ml - final_target_units_ml
                extra_info += f"; for {arg_unit_target} units (UK), " \
                              f"it must become {final_target_units_ml}ml at {arg_percent}% " \
                              f"or must remove {final_remove_amount}ml from the total amount"
            elif arg_target_percent != 0:
                final_target_percent = int((arg_percent/arg_target_percent)*arg_ml-arg_ml)
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

    async def target_sleeps(self, target):
        now = datetime.datetime.now()
        xtra_msg = ''

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
            xtra_msg = f"({self.target_sleeper} has sent a message: {self.detected_sleeper.hour}:{detected_minutes})"

        await self.message(target, f"chance {self.target_sleeper} to sleep now: {round(final_percent, 2)}% {xtra_msg}")

    async def mixalcohol(self, target):
        await self.message(target, "mix alcohol info: https://pastebin.com/raw/9LZCqNg0 ; "
                                   "links: https://imgur.com/a/vzaiwSN (layering demo) ; "
                                   "https://www.goodcocktails.com/bartending/specific_gravity.php (specific gravity)")

    async def regex_sixnine(self, target):
        await self.message(target, "nice")

    async def on_message(self, target, source, message):
        bridge_name = True
        if self.only_bridge is True and source != self.bridge_bot_name:
            bridge_name = False

        if source != bot_name and 1 < len(message) < 256 and bridge_name is True:
            regex = False

            if self.use_regex is True:
                regex = await self.check_regex_username(message)
                if regex is True:
                    got_username = self.got_username
                else:
                    got_username = source
            else:
                got_username = source

            if self.debug is False and message.startswith(str(self.got_regex)) and source != self.bridge_bot_name:
                logging.warning(f"{source} is attempting to use the bridge pattern: {message}")
                return

            if regex is True:
                message = message.replace(self.got_regex, '')

            if message == '':
                logging.info(f"empty message by {got_username}")
                return

            logging.info(f"got_username:{got_username}")

            try:
                parsed_toml_global_sleeper = toml.load("sleeper_table.toml")
            except FileNotFoundError:
                await self.message(target, f"the sleeper table doesn't exist")
                return
            else:
                sleeper_usernames = parsed_toml_global_sleeper["sleeper_usernames"]
                self.all_hours = parsed_toml_global_sleeper["hour"]
                self.target_sleeper = parsed_toml_global_sleeper["show_as"]

            if got_username in sleeper_usernames:
                self.detected_sleeper = datetime.datetime.now()

            try:
                logging.info(f"self.banned_list[got_username]: {self.banned_list[got_username]}")
                logging.info(
                    f"self.already_banned_list[got_username]: {self.already_banned_list[got_username]}")
                calc_wait_time = pow((self.wait_time_list + len(self.already_banned_list[got_username])), 2)
                logging.info(f"calc_wait_time: {calc_wait_time}")
                if datetime.datetime.now() - self.banned_list[got_username] \
                        >= datetime.timedelta(seconds=calc_wait_time):
                    self.banned_list.pop(got_username)
                    logging.info(f"Removing: {got_username} from banned_list")

                    if datetime.datetime.now() - self.already_banned_list[got_username][-1] \
                            >= datetime.timedelta(seconds=calc_wait_time * 2):
                        self.already_banned_list.pop(got_username)
                        logging.info(f"Removing: {got_username} from already_banned_list")
                else:
                    return
            except KeyError:
                pass

            regex_result = dict()

            for rx in parsed_commands.get("regex"):
                if await check_regex_true(rx, message) is True:
                    regex_result[rx] = True

            logging.info(f"regex_result: {regex_result}")

            for item in parsed_commands.get("command"):
                values = parsed_commands["command"].get(item)
                extra = values.get("extra")
                method = values.get("method")

                for ext_item in extra:
                    if message.startswith(f"{comm_char}{item}") or \
                            message.startswith(f"{comm_char}{ext_item}") or \
                            bool(regex_result) is True:
                        if self.last_time is None:
                            self.last_time = datetime.datetime.now()
                        elif datetime.datetime.now() - self.last_time <= datetime.timedelta(
                                seconds=self.wait_time_commands):
                            logging.info(f"wait time detected for: {got_username}")
                            await self.message(target, f"{got_username} less than 1 second "
                                                       f"difference with last message (might not be yours)")
                            return

                        self.last_time = datetime.datetime.now()
                        logging.info(f"self.last_time: {self.last_time}")

                        try:
                            buffer_size = 2
                            if len(self.last_time_buffer[got_username]) == buffer_size:
                                self.last_time_buffer[got_username].pop(0)

                            self.last_time_buffer[got_username].append(datetime.datetime.now())
                        except KeyError:
                            self.last_time_buffer[got_username] = [datetime.datetime.now()]
                        else:
                            allowed_time_differance_seconds = 3
                            calc_time_differance = 0
                            for time in self.last_time_buffer[got_username]:
                                calc_time_differance = time.timestamp() - calc_time_differance
                            logging.info(f"calc_time_differance: {calc_time_differance}")
                            if calc_time_differance <= allowed_time_differance_seconds:
                                try:
                                    self.already_banned_list[got_username]
                                except KeyError:
                                    self.already_banned_list[got_username] = [datetime.datetime.now()]
                                else:
                                    self.already_banned_list[got_username].append(datetime.datetime.now())
                                self.banned_list[got_username] = datetime.datetime.now()
                                detected_time_msg = \
                                    f"Detected {got_username} bellow allowed_time_differance_seconds: " \
                                    f"{allowed_time_differance_seconds}"
                                logging.warning(detected_time_msg)
                                await self.message(target, f"{got_username} is spamming, ignoring messages for a bit")

                        logging.info(f"detected messsage: {message} by {got_username}")
                        if target == bot_name:
                            logging.info(f"messages is pm by {got_username}, setting target")
                            target = got_username
                        split_m = message.split(maxsplit=1)
                        if len(split_m) > 1:
                            argument = split_m[1]
                        else:
                            argument = None

                        if message.startswith(f"{comm_char}{item}") or \
                                message.startswith(f"{comm_char}{ext_item}"):
                            if argument == "help":
                                await self.help_method(target, item)
                                return

                            if method == "help_method()":
                                await self.help_method(target, argument)
                            elif method == "target_sleeps()":
                                await self.target_sleeps(target)
                            elif method == "pingme()":
                                await self.pingme(target, argument)
                            elif method == "ping_ports()":
                                await self.ping_ports(target)
                            elif method == "ideas()":
                                await self.ideas(target, f"{got_username}:{argument}")
                            elif method == "add_idea()":
                                await self.add_idea(target, f"{got_username}:{argument}")
                            elif method == "remove_idea()":
                                await self.remove_idea(target, f"{got_username}:{argument}")
                            elif method == "alcohol()":
                                await self.alcohol(target, argument)
                            elif method == "mixalcohol()":
                                await self.mixalcohol(target)
                        for rx in regex_result:
                            if parsed_commands["regex"].get(rx).get("method") == "regex_sixnine()":
                                await self.regex_sixnine(target)
                        return
            if message.startswith(comm_char):
                await self.message(target, f"there's no such command: {message}")


client = MyOwnBot(nickname=bot_name,
                  realname="Bruh Bot",
                  sasl_username=sasl_username,
                  sasl_password=sasl_password,
                  sasl_mechanism=sasl_mechanism)
client.RECONNECT_MAX_ATTEMPTS = 6
client.run(hostname=host, port=port, tls=tls, tls_verify=tls_verify, password=password)
