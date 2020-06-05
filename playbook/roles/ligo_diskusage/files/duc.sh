#!/bin/bash


url_array=( ${SCRIPT_NAME//// } )
url_length="${#url_array[@]}"


if [ "${url_length}" -eq 1 ]; then
    user="$uid"
else
    user=${url_array[1]}
    ducoptions=""
    
    if [ $url_length -gt "2" ] && [ ${url_array[2]} == "count" ]; then
	ducoptions+=" --count"
    fi

fi

if [ -z "$QUERY_STRING" ]; then
    export QUERY_STRING="path=/home/$user"
fi


/bin/duc cgi -d /home/${user}/.duc.db --list --tooltip $ducoptions \
    --header=<( sed "s/USER/$user/g;  s|QUERY|${QUERY_STRING/&/\&}|g" /srv/diskusage/header.html )
