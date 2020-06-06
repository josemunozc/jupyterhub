#!/bin/sh
/root/bin/home_backup.sh $1 > /var/log/home_backup_$( date +"%m%d" ).log 2>&1

