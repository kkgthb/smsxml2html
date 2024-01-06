#!/usr/bin/env python3

# SMS XML to HTML
# By Christopher Mitchell, Ph.D.
# https://github.com/smsxml2html

import os
from lxml import etree
from lxml.etree import XMLParser
import argparse
import base64
import re
import datetime
import locale
from collections import defaultdict
import copy

STYLESHEET_TEMPLATE = """
.msg_date, .msg_sender_incoming, .msg_sender_outgoing {
    font-family: 'Courier New', monospaced;
    font-size: 0.75em;
    white-space: nowrap;
}
.msg_date {
    color: #600000;
}
.msg_sender_incoming {
    color: #000060;
}
.msg_sender_incoming::before {
    content: " << ";
}
.msg_sender_outgoing {
    color: #006000;
}
.msg_sender_outgoing::before {
    content: " >> ";
}
.mms_img {
    max-height: 50vh;
    border: 0;
}
.month_convos tr, .month_convos td {
    vertical-align: text-top;
}
.toc {
    -moz-column-width: 30em;
    -webkit-column-width: 30em;
    column-width: 30em;
}
"""


class SMSMsg:
    def __init__(self, timestamp, text, type_, contact_name):
        self.timestamp = timestamp
        self.text = text
        self.type_ = type_
        self.contact_name = contact_name


class MMSMsg(SMSMsg):
    def __init__(self, contact_name, timestamp=0, text="", type_=1):
        SMSMsg.__init__(self, timestamp, text, type_, contact_name)
        self.images = []

    def add_image(self, base_path, timestamp, name, mime, data):
        if mime == 'image/png':
            ext = 'png'
        elif mime == 'image/jpeg':
            ext = 'jpg'
        elif mime == 'image/gif':
            ext = 'gif'
        else:
            print("Unknown MIME type '%s' for MMS content; omitting content" % mime)
            return

        name = str(timestamp) + re.sub('[^A-Za-z0-9_.-]+', '', name) + '.' + ext
        out_path = os.path.join(base_path, name)
        with open(out_path, 'wb') as f:
            try:
                f.write(base64.b64decode(data))
            except TypeError:
                print("Failed to decode base64 for image %s" % name)
                return
        self.images.append(name)


def parse_carrier_number(number):
    number = re.sub('[^0-9]', '', number)
    if len(number) == 10:
        number = '1' + number
    return number


def parse_conversations(root, conversations, users, base_path, carrier_number):
    messages = 0
    for child in root:
        if child.tag == 'sms':
            address = parse_carrier_number(child.attrib['address'])
            date = int(child.attrib['date'])  # Epoch timestamp
            type_ = child.attrib['type']  # 2 = outgoing, 1 = incoming
            name = child.attrib['contact_name']
            body = child.attrib['body']

            save_msg = SMSMsg(date, body, type_, name)
            conversations[address][date] = save_msg
            messages += 1

            if name and address not in users:
                users[address] = name

        elif child.tag == 'mms':
            save_msg = MMSMsg(contact_name=child.attrib['contact_name'])
            date = int(child.attrib['date'])  # Epoch timestamp
            addresses = {}
            for mms_child in child:
                if mms_child.tag == 'parts':
                    for part_child in mms_child:
                        if part_child.tag == 'part':
                            part_name = part_child.attrib['name']
                            part_data = part_child.attrib.get('data', "")
                            part_text = part_child.attrib.get('text', "")
                            part_mime = part_child.attrib['ct']
                            if "image" in part_mime:
                                save_msg.add_image(base_path, date, part_name, part_mime, part_data)
                            elif "text" in part_mime:
                                save_msg.text += part_text
                elif mms_child.tag == 'addrs':
                    for addr_child in mms_child:
                        if addr_child.tag == 'addr':
                            parsed_child_address = parse_carrier_number(addr_child.attrib['address'])
                            if carrier_number != parsed_child_address:
                                addresses[parsed_child_address] = addr_child.attrib['type']

            # attempt to fix missing phone numbers
            if "" in addresses.keys():  # there is a missing number
                if carrier_number in addresses.keys():
                    # the missing number isn't the carrier number, so where did the message come from
                    # or go to???
                    print("failed to fix missing phone number in message")
                else:  # assume that the message was sent by the carrier number
                    if len(addresses.keys()) == 1:  # message to self?
                        addresses[carrier_number] = addresses[""]  # copy type over, but either should work
                    del addresses[""]

            for address, type_ in addresses.items():
                new_msg = copy.deepcopy(save_msg)
                new_msg.address = address
                new_msg.type_ = type_
                new_msg.timestamp = date
                conversations[address][date] = new_msg
                messages += 1

    return messages  # Count of messages


def dump_conversations(base_path, conversations, real_carrier_number):
    files = 0

    with open(os.path.join(base_path, 'stylesheet.css'), 'w', encoding='utf-8') as f:
        f.write(STYLESHEET_TEMPLATE)

    for address, conversation in conversations.items():
        output_path = os.path.join(base_path, address + '.html')

        with open(output_path, 'w', encoding='utf-8') as f:

            f.write('<!DOCTYPE html><html><head><meta charset="UTF-8">')
            f.write('</head><body>' + "\n")

            # Generate the TOC
            prev_month_year = ""
            months = []
            month_amap = {}
            for date in sorted(conversation.keys()):
                msg = conversation[date]
                dt = datetime.datetime.utcfromtimestamp(msg.timestamp / 1000)
                month_year = dt.strftime('%B %Y')
                if month_year != prev_month_year:
                    month_year_short = dt.strftime('%y%m')
                    months.append(month_year)
                    month_amap[month_year] = month_year_short
                prev_month_year = month_year

            # Generate the TOC
            f.write('<nav><h1 id="toc">Jump to a specific month</h1><ul>')
            for month_year in months:
                f.write('<li><a href="#%s">%s</a>' % (month_amap[month_year], month_year))
            f.write('</ul></nav><hr/><hr/>')

            # Generate the body
            prev_month_year = ""
            f.write('<main><h1 id="main">Conversations by month</h1>')
            for date in sorted(conversation.keys()):
                msg = conversation[date]
                dt = datetime.datetime.utcfromtimestamp(msg.timestamp / 1000)
                month_year = dt.strftime('%B %Y')
                if month_year != prev_month_year:
                    if prev_month_year != '':
                        f.write('</section>')
                    f.write('<hr/>')
                    f.write('<section class="month_convos" id="%s">' % month_amap[month_year])
                    f.write("<h2>~~ %s ~~</h2>\n" % month_year)
                f.write('<article class="one_message">')
                f.write('<h3><font color="#600000">%s</font></h3>' % dt.strftime('%m/%d/%y %I:%M:%S%p'))
                from_number = address if msg.type_ in ["1", "137"] else real_carrier_number
                to_number = real_carrier_number if msg.type_ in ["1", "137"] else address
                my_color = '006000'
                their_color = '000060'
                my_name = ' <i>(this phone)</i>'
                their_name = ' <i>({a_name})</i>'.format(a_name = getattr(msg, "contact_name", 'throwaway_text')) if (hasattr(msg, 'contact_name') and getattr(msg, 'contact_name') != '(Unknown)') else ''
                if (from_number == to_number and their_name != my_name):
                    their_name = ' <i>(???)</i>'
                sender = "incoming" if msg.type_ in ["1", "137"] else "outgoing"
                f.write(
                    '<h4 class="msg_sender">{direction}:  from <font color="#{from_color}">{from_number}</font>{from_name} to <font color="#{to_color}">{to_number}</font>{to_name}</h4>'.format(
                        direction=sender.title(), 
                        from_number=from_number, 
                        to_number=to_number, 
                        from_color=(their_color if sender == 'incoming' else my_color), 
                        to_color=(my_color if sender == 'incoming' else their_color),
                        from_name=(their_name if sender == 'incoming' else my_name), 
                        to_name=(my_name if sender == 'incoming' else their_name)
                        )
                    )
                f.write('<p class="msg_body">%s' % msg.text)
                if isinstance(msg, MMSMsg):
                    f.write('<br />')
                    for image in msg.images:
                        f.write('<a href="%s"><img class="mms_img" src="/%s" /></a> ' % (image, image))
                f.write('</p>')
                f.write('</article><hr align="left" width="20%" color="#808080">\n')
                prev_month_year = month_year

            f.write("</section>\n")
            f.write("</main></body></html>")
        files += 1
    return files


def main():
    # parse options and get results
    parser = argparse.ArgumentParser(description='Turns SMS Backup and Restore XML into HTML conversations with images')
    parser.add_argument('input', metavar='input', nargs='+', type=str, help='Input XML file')
    parser.add_argument('-o', '--output', type=str, required=True, help='Output directory')
    parser.add_argument('-d', '--dummy_number', type=str, required=True, help='User\'s dummy carrier number')
    parser.add_argument('-r', '--real_number', type=str, required=True, help='User\'s real carrier number')
    args = parser.parse_args()
    dummy_carrier_number = parse_carrier_number(args.dummy_number)
    real_carrier_number = parse_carrier_number(args.real_number)

    messages = 0
    conversations = defaultdict(dict)
    users = {}
    locale.setlocale(locale.LC_ALL, '')
    for input_ in args.input:
        # Open the input file
        lxml_parser = XMLParser(huge_tree=True, recover=True)
        tree = etree.parse(input_, parser=lxml_parser)
        root = tree.getroot()

        # Parse it out
        try:
            os.mkdir(args.output)
        except OSError:
            pass  # Already exists
            print("Parsing conversations from %s" % input_)
        messages += parse_conversations(root, conversations, users, args.output, dummy_carrier_number)

    print("Parsed %d messages in %d conversations with %d known user names" %
          (messages, len(conversations), len(users)))
    files = dump_conversations(args.output, conversations, real_carrier_number)
    print("Dumped messages to %d conversation HTML files" % files)


if __name__ == '__main__':
    main()
