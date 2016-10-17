#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging, telegram
from amazon.api import AmazonAPI


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Create a client instance to query Amazon API.
amazon = AmazonAPI("", "", "")

# Define states for search conversation
SELECT_RESULT, BOOK_TITLE = range(2)

# Cache search results for each conversation in a dict
# user ID -> list of results
search_results = dict()

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.

def start(bot, update):

    bot.sendMessage(update.message.chat_id, text='This bot can help you recommend a book.\n'
                                                 'Write /find to find a book 📚👓',
                    parse_mode=telegram.ParseMode.MARKDOWN)


def find(bot, update):

    bot.sendMessage(update.message.chat_id, text= 'Write the title of the last book that you read.')
    return BOOK_TITLE


def search(bot, update):

    # Get user info.
    user = update.message.from_user

    logger.info("%s searched for: %s" % (user.first_name, update.message.text))

    # Search for the book
    products1 = amazon.search(Keywords=update.message.text, SearchIndex='Books')

    # List of result
    results = list()

    bookList = ''

    # Search database and fill list
    try:
        for i, product in enumerate(products1):
            results.append(product)
            if (product.title.find(':') != -1):
                bookList += '/' + str(i + 1) + ' ' + product.title[product.title.find(':'):] + '.' + '\n'
            elif (product.title.find('(') != -1):
                bookList += '/' + str(i + 1) + ' ' + product.title[product.title.find('('):] + '.' + '\n'
            elif (product.title.find('-') != -1):
                bookList += '/' + str(i + 1) + ' ' + product.title[product.title.find('-'):] + '.' + '\n'
            elif (product.title.find('-') != -1):
                bookList += '/' + str(i + 1) + ' ' + product.title[product.title.find('-'):] + '.' + '\n'
            else:
                bookList += '/' + str(i+1) + ' ' + product.title + '.' + '\n'

            if i > 3:
                break
        # Cache search results
        search_results[user.id] = results

    except:
        bookList = 'Your search did not match any book. \n*Try something like:'+\
                   '*✏️ Check your spelling.\n✏️ Search by author or ISBN.'

    # Send message with list of results
    bot.sendMessage(update.message.chat_id, text=bookList, parse_mode=telegram.ParseMode.MARKDOWN)

    # Switch to the SELECT_RESULT state
    return SELECT_RESULT


def select(bot, update, groupdict):

    # Load cached result list and pick
    results = search_results[update.message.from_user.id]
    selected_result_nr = int(groupdict['result'])
    selected_result = results[selected_result_nr - 1]

    logger.info("SELECTED BOOK: %s" % (selected_result.title))

    # Look for recommendations
    products = amazon.similarity_lookup(ItemId=selected_result.asin)

    # Search results
    results = list()
    bookList = ''

    for i, prod in enumerate(products):
        results.append(prod)
        bookList += '/' + str(i+1) + ' ' + prod.title + '.' + '\n'
        if i > 1:
            break

    # Send message with list of results
    bot.sendMessage(update.message.chat_id, text='Here are some books you might like 😉\n' + bookList,
                    parse_mode=telegram.ParseMode.MARKDOWN)

    # Exit the conversation
    return ConversationHandler.END


def similarty(bot, update):
    products1 = amazon.search(Keywords=update.message.text, SearchIndex='Books')
    for i, product in enumerate(products1):
        if i > 2:
            break
        products = amazon.similarity_lookup(ItemId=product.asin)
        for i, prod in enumerate(products):
            bot.sendMessage(update.message.chat_id, text="{0}. '{1}'".format(i + 1, prod.title))
            if i > 1:
                break


'''def top(bot, update):
    bn = amazon.browse_node_lookup(BrowseNodeId=1000, 'TopSellers')
    bot.sendMessage(update.message.chat_id, text=bn.name)
'''

'''root_ids = result.xpath(
     '//aws:BrowseNode[aws:IsCategoryRoot=1]/aws:BrowseNodeId',
     namespaces={'aws': result.nsmap.get(None)})
    i = 1
    result = amazon.browse_node_lookup(root_ids[1000], 'TopSellers')
    for  item in result.BrowseNodes.BrowseNode.TopSellers.TopSeller:
        bot.sendMessage(update.message.chat_id, text= "{0}. '{1}'".format(i, item.title))
        i = i+1
        if i > 1:
break '''


def help(bot, update):
    bot.sendMessage(update.message.chat_id, text='Help!')


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():

    # Create the EventHandler and pass it your bot's token.
    updater = Updater("Token")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    # dp.add_handler(CommandHandler("help", help))

    # on noncommand i.e message - find the book on Telegram
    # dp.add_handler(MessageHandler([Filters.text], search))

    # Add conversation handler with the states SELECT_RESULT
    search_conv = ConversationHandler(
        entry_points=[CommandHandler('find', find)],
        # entry_points=[CommandHandler('start', start)],
        states={
            BOOK_TITLE: [MessageHandler([Filters.text], search)],
            SELECT_RESULT: [RegexHandler(r'^/(?P<result>\d+).*$', select, pass_groupdict=True)]
        },
        fallbacks=[]
    )

    dp.add_handler(search_conv)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
