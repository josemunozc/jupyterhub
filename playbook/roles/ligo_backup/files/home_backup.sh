#!/bin/bash
set -u

tag=$1

function backup() {
    index=$1
    directory=$2
    job=$3

    echo -n $index $job $directory $( date +"%F_%T" )" "
    [ ! -d /gluster/ligo-ds/home-backup/$directory ] &&
        mkdir -m 0750 /gluster/ligo-ds/home-backup/$directory &&
	chgrp LIGO /gluster/ligo-ds/home-backup/$directory

    /bin/time -f "%E" /usr/local/bin/rsnapshot -c <( sed 's/$USER/'$directory'/g' /etc/rsnapshot_by_user.conf ) $tag
}

export -f backup
export tag

directories=$( cut -d"\"" -f 3 /etc/grid-security/grid-mapfile | cut -d"," -f 1 | tr -d " " | sort -uR )

echo "$directories" | parallel --jobs 6 backup {#} {} {%}

date
