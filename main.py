import sqlite3
import os
from discord.client import Client
from dotenv import load_dotenv
from discord.ext import commands
from discord import Intents
from discord.utils import get
from keys import discord_key

from datetime import datetime
intents = Intents(messages=True, guilds=True)
load_dotenv()
#TOKEN = os.getenv('THE_COUNT_DISCORD_TOKEN')
TOKEN = discord_key()
#PREFIX = "".join((os.getenv('THE_COUNT_PREFIX'), ' '))
PREFIX = "!count "
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

DbName = 'count.sqlite'
count_info_headers = ['guild_id', 'current_count', 'number_of_resets', 'last_user', 'message', 'channel_id', 'log_channel_id', 'greedy_message', 'record', 'record_user', 'record_timestamp']
stat_headers = ['user', 'count_correct', 'count_wrong', 'highest_valid_count', 'last_activity']
beer_headers = ['user', 'owed_user', 'count']
connection = sqlite3.connect(DbName)
cursor = connection.cursor()


# -- Begin SQL Helper Functions --
def create_table(dbname, tablename, tableheader):
    try:
        cursor.execute("CREATE TABLE %s%s" % (tablename, tuple(tableheader)))
        connection.commit()
        return
    except sqlite3.OperationalError:
        return


def insert_values_into_table(dbname, tablename, values):
    if os.path.exists(dbname) is True:
        cursor.execute("INSERT INTO %s VALUES %s" % (tablename, tuple(values)))
        connection.commit()


def check_if_table_exists(dbname, tablename, tableheaders):
    try:
        cursor.execute("SELECT * FROM %s" % tablename)
    except sqlite3.OperationalError:
        create_table(dbname, tablename, tableheaders)


def create_new_entry(guild_id,
                     count=str(0),
                     number_of_resets=str(0),
                     last_user=str(0),
                     guild_message=str("{{{user}}} typed the wrong number"),
                     count_channel_id=str(''),
                     log_channel_id=str(''),
                     greedy_message=str("{{{user}}} was too greedy")):
    # dbOperations.put(['create',
    temp1 = [
        str(guild_id), str(count),
        str(number_of_resets),
        str(last_user),
        str(guild_message),
        str(count_channel_id),
        str(log_channel_id),
        str(greedy_message),
        str(0),
        str(0),
        str(0)]
    # ])
    check_if_table_exists(DbName, f'stats_{guild_id}', stat_headers)
    check_if_table_exists(DbName, f'beers_{guild_id}', beer_headers)
    cursor.execute("INSERT INTO count_info %s VALUES %s" % (tuple(count_info_headers), tuple(temp1)))
    connection.commit()
    return

def update_beertable(guild_id, user, owed_user, count, second_try=False):
    cursor.execute(f"SELECT * FROM beers_{guild_id} WHERE user = '{user}' AND owed_user = '{owed_user}'")
    temp = cursor.fetchone()
    if temp is None:
        if second_try is True:
            cursor.execute(f"INSERT INTO beers_{guild_id} (user, owed_user, count) VALUES ('{owed_user}','{user}', '1')")
            connection.commit()
        else:
            update_beertable(guild_id, owed_user, user, -count, second_try=True) #Changed user and owed_user on purpose
        

    else:
        cursor.execute(f"UPDATE beers_{guild_id} SET count = count + {count} WHERE user = '{user}' AND owed_user = '{owed_user}'")
        connection.commit()

def update_stats(guild_id, user, correct_count = True, current_number = 1):
    # stat_headers = ['user', 'count_correct', 'count_wrong', 'highest_valid_count', 'last_activity']
    
    cursor.execute(f"SELECT * FROM stats_{guild_id} WHERE user = '{user}'")
    temp = cursor.fetchone()
    last_activity = datetime.now() 
    if temp is None:
        if correct_count is True:
            cursor.execute(f"INSERT INTO stats_{guild_id} (user, count_correct, count_wrong, highest_valid_count, last_activity) VALUES ('{user}', '1', '0', '{current_number}', '{last_activity}')")
        else:
            cursor.execute(f"INSERT INTO stats_{guild_id} (user, count_correct, count_wrong, highest_valid_count, last_activity) VALUES ('{user}', '0', '1', '{current_number}', '{last_activity}')")
        connection.commit()
    else:
        highest_valid_count = temp[3]
        if current_number > int(highest_valid_count):
            highest_valid_count = str(current_number)
        if correct_count is True:
            cursor.execute(f"UPDATE stats_{guild_id} SET count_correct = count_correct + 1, highest_valid_count = ?, last_activity = ? WHERE user = '{user}'", (highest_valid_count, last_activity,))
        else:
            cursor.execute(f"UPDATE stats_{guild_id} SET count_wrong = count_wrong + 1, last_activity = ? WHERE user = '{user}'", (last_activity,))
        connection.commit()

def update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp,  table_name='count_info'):
    cursor.execute(f"UPDATE {table_name} SET guild_id = ?, current_count = ?, number_of_resets = ?, last_user = ?, message = ?, channel_id = ?, log_channel_id = ?, greedy_message = ?, record = ?, record_user = ?, record_timestamp = ? WHERE guild_id = '{guild_id}'", (guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message,record, record_user, record_timestamp, )) 
    connection.commit()
# -- End SQL Helper Functions --


# -- Begin Count Master Commands --
bot.remove_command('help')


@bot.command(name='help')
async def count_help(ctx):
    response = """See https://github.com/bloedboemmel/Discord-Counting-Bot for detailed help info"""
    await ctx.send(response)
    return


@bot.command(name='wrong_message')
@commands.has_role("count master")
async def wrong_message(ctx, *args):
    _message = " ".join(args)
    if _message == 'help':
        response = """
        Set the message to be sent when someone types the wrong number
{{{user}}} will be replaced by the name of whoever typed the wrong number
        """
        await ctx.send(response)
        return
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    test = cursor.fetchone()

    
    if test is None:
        create_new_entry(ctx.guild.id,
                         count_channel_id=ctx.channel.id,
                         log_channel_id=ctx.channel.id,
                         guild_message=_message)
    else:
        guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp = test
        update_info(guild_id, count, number_of_resets, last_user, _message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp)
    return


@wrong_message.error
async def wrong_message_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You need the role "count master" to run that command')
    else:
        raise error


@bot.command(name='greedy_message')
@commands.has_role("count master")
async def greedy_message(ctx, *args):
    _message = " ".join(args)
    if _message == 'help':
        response = """
        Set the message to be sent when someone types 2 messages in a row
{{{user}}} will be replaced by the name of whoever typed the 2 messages
        """
        await ctx.send(response)
        return
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    test = cursor.fetchone()
    if test is None:
        create_new_entry(ctx.guild.id,
                         count_channel_id=ctx.channel.id,
                         log_channel_id=ctx.channel.id,
                         greedy_message=_message)
        
    else:
        guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, old_greedy_message, record, record_user, record_timestamp = test
        update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, _message, record, record_user, record_timestamp)
    return


@wrong_message.error
async def wrong_message_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You need the role "count master" to run that command')
    else:
        raise error


@bot.command(name='counting_channel')
@commands.has_role("count master")
async def counting_channel(ctx, arg1):
    print("counting_channel")
    channel_id = arg1
    if channel_id == 'help':
        response = """
            Set the id of the channel that you want to count in
use `!count counting_channel this_channel` to use the channel that you are typing in
            """
        await ctx.send(response)
        return
    if channel_id == 'this_channel':
        channel_id = ctx.channel.id
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    test = cursor.fetchone()
    
    
    if test is None:
        create_new_entry(ctx.guild.id,
                         count_channel_id=channel_id,
                         log_channel_id=channel_id,)
    else:
        guild_id, count, number_of_resets, last_user, guild_message, old_channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp = test
        update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp)
    return


@counting_channel.error
async def counting_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You need the role "count master" to run that command')
    else:
        raise error


@bot.command(name='log_channel')
@commands.has_role("count master")
async def log_channel(ctx, arg1):
    print("log_channel")
    channel_id = arg1
    if channel_id == 'help':
        response = """
            Set the id of the channel that you want to log mistakes too
use `!count log_channel this_channel` to use the channel that you are typing in
            """
        await ctx.send(response)
        return
    if channel_id == 'this_channel':
        channel_id = ctx.channel.id
        
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    test = cursor.fetchone()
    if test is None:
        create_new_entry(ctx.guild.id,
                         count_channel_id=channel_id,
                         log_channel_id=channel_id,)
    else:
        guild_id, count, number_of_resets, last_user, guild_message, old_channel_id, old_log_channel_id, greedy_message, record, record_user, record_timestamp = test
        update_info(guild_id, count, number_of_resets, last_user, guild_message, old_channel_id, channel_id, greedy_message, record, record_user, record_timestamp)
    return


@counting_channel.error
async def counting_channel_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('You need the role "count master" to run that command')
    else:
        raise error

# -- End Count Master Commands --
# -- Begin Beer Count Commands --
@bot.command(name='beer_count')
async def beer_count(ctx, args1 = ""):
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    temp = cursor.fetchone()
    if temp is None:
        print("No log_channel for beer_score")
        return
    elif temp[6] != ctx.channel.id:
        print("Wrong channel for beer_score")
        return
    print("beer_count")
    if args1 == 'me':
        cursor.execute(f"SELECT * FROM beers_{ctx.guild.id} WHERE user = '{ctx.message.author.id}' ORDER BY count DESC")
    else:
        cursor.execute(f"SELECT * FROM beers_{ctx.guild.id} ORDER BY count DESC")
    db_restults = cursor.fetchall()
    for result in db_restults:
        user1, user2, count = result
        if user1 == '' or user2 == '':
            continue
        await ctx.send(f"<@{user2}> ows <@{user1}> {count} beers")

@bot.command(name='highscore')
async def highscore(ctx):
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % ctx.guild.id)
    temp = cursor.fetchone()
    if temp is None:
        print("No log_channel for highscore")
        return
    elif temp[6] != ctx.channel.id:
        print("Wrong channel for highscore")
        return
    print("highscore")
    cursor.execute(f"SELECT * FROM stats_{ctx.guild.id} ORDER BY count DESC")
    db_restults = cursor.fetchall()
    i = 1
    for result in db_restults:
        user1, count = result
        if user1 == '':
            continue
        await ctx.send(f"<@{user1}>: {count}")
        if i == 10:
            break
        i += 1


# -- Begin Edit Detection --
@bot.event
async def on_message_edit(before, after):
    if before.content != after.content:
        if 'substring' in after.content:
            print("Thats son of a bitch edited!")

# -- Begin counting detection --
@bot.event
async def on_message(_message):
    ctx = await bot.get_context(_message)
    if ctx.message.author.bot:
        return
    if str(_message.content).startswith(str(PREFIX)):
        await bot.invoke(ctx)
        return
    cursor.execute("SELECT * FROM count_info WHERE guild_id = '%s'" % _message.guild.id)
    temp = cursor.fetchone()
    if temp is None:
        print("ln 143")
        return
    else:
        print(temp[5])
        print(_message.channel.id)
        if str(temp[5]) != str(ctx.channel.id):
            print("ln 147")
            return
        else:
            print("ln 150")
            try:
                current_count, trash = _message.content.split(' ', 1)
            except ValueError:
                current_count = _message.content
            current_count = int(current_count)
            print(current_count)
            old_count = int(temp[1])
            print(old_count)
            if str(ctx.message.author.id) == str(temp[3] +"test"):
                print("greedy")
                guild_id, old_count, old_number_of_resets, old_last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp = temp
                count = str(0)
                number_of_resets = str(int(old_number_of_resets) + 1)
                last_user = str('')
                update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp)

                await ctx.send(str(temp[7]).replace("{{{user}}}", '<@%s>' % str(ctx.message.author.id)))
                channel = bot.get_channel(int(temp[6]))
                await channel.send('<@%s> lost the count when it was at %s' % (ctx.message.author.id, old_count))
                await ctx.message.add_reaction('💀')
                return
            if old_count + 1 != current_count:
                guild_id, old_count, old_number_of_resets, old_last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp = temp
                count = str(0)
                number_of_resets = str(int(old_number_of_resets) + 1)
                last_user = str('')
                beers_last_user = str(ctx.message.author.id)
                update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp)

                await ctx.send(str(temp[4]).replace("{{{user}}}", '<@%s>' % str(ctx.message.author.id)))
                
                channel = bot.get_channel(int(temp[6]))
                await ctx.message.add_reaction('❌')
                await channel.send('<@%s> lost the count when it was at %s and has to give <@%s> a beer!' % (ctx.message.author.id, old_count, old_last_user))
                #if beers_last_user == old_last_user:
                #    return
                update_beertable(guild_id, beers_last_user, old_last_user, +1)
                update_stats(guild_id, beers_last_user, correct_count=False)
                return
            if old_count + 1 == current_count:
                guild_id, old_count, number_of_resets, old_last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp = temp
                
                count = str(current_count)
                last_user = str(ctx.message.author.id)
                if int(record) < current_count:
                    record = count
                    record_user = str(ctx.message.author.id)
                    record_timestamp = datetime.now()
                update_info(guild_id, count, number_of_resets, last_user, guild_message, channel_id, log_channel_id, greedy_message, record, record_user, record_timestamp)
                update_stats(guild_id, ctx.message.author.id, current_number= current_count)
                await ctx.message.add_reaction('✅')
                return
            return


# -- Begin Initialization code --
check_if_table_exists(DbName, 'count_info', count_info_headers)
# create_new_entry(0)
# t = threading.Timer(0, run_queue)
# t.start()
# print("passed_threading")
bot.run(TOKEN)
# -- End Initialization code --
