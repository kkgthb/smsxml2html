# smsxml2html

Made even further modifications of [ackermanaviation fork](https://github.com/ackermanaviation/smsxml2html) as found in [original project issue #3](https://github.com/KermMartian/smsxml2html/issues/3#issuecomment-1364458161).

Outputs as full-width HTML divided up with section and article tags and such, not as a table, so that it prints better from web browsers to PDF or paper.

_(Or try converting it to Word with Pandoc -- this is one reason there is no CSS -- sadly, though, this script still needs a little work because Pandoc on Windows is lousy at parsing relative image paths.)_

## Turn SMS Backup and Restore SMS XML files into HTML transcripts
By Chistopher Mitchell, Ph.D.

_(futher modified by [ackermanaviation](https://github.com/ackermanaviation) and [Katie Kodes](https://katiekodes.com/))_

This tool creates HTML transcripts of SMS/MMS conversations from
[Carbonite SMS Backup and Restore](https://www.carbonite.com/en/apps/call-log-sms-backup-restore)
backup files. It takes one or more XML files, separates them out into one-on-one conversations,
and emits each of those conversations as a separate HTML file. It also parses the URI-encoded
MMS images in these backups and produces picture files you can view, edit, and organize.

Usage
-----
    python smsxml2html.py -o <output_dir> -d <some_sort_of_nonexistent_impossible_phone_number> -r <user_carrier_number> <input_file> [<input_file> ...]

  * <output_dir>: New directory into which to place HTML files and images
  * <some_sort_of_nonexistent_impossible_phone_number>: Something nonexistent, in `1NNNXXXYYYY` format, like `10000000000` _(helps ensure texts to self still process)_
  * <user_carrier_number>: The carrier number of the SMS backups' owner, in `1NNNXXXYYYY` format
  * <input_file>: One or more XML backup files produced by SMS Backup and Restore.