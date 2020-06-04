#!/bin/bash

owner_certs=$( condor_q -constraint "x509userproxy isnt undefined" -af: owner x509userproxy | sort | uniq -c)
users=$( echo  "$owner_certs" | awk '{ print $2 }' | sort -u )

for user in $users; do
  if [ -e /home/$user/.no_x509_warning_mail ]; then
    continue
  fi
  certs=$( echo "$owner_certs" | grep $user | awk '{ print $3}' )

  reason=()
  for cert in $certs; do
    openssl x509 -in $cert -checkend 259200 -noout  2>/dev/null
    if [ $? -ne 0 ] ; then
	count=$(  echo "$owner_certs" | grep $cert | awk '{ print $1 }' );
        if [ -f $cert ];  then
  	  openssl x509 -in $cert -checkend 0 -noout
  	  if [ $? -ne 0 ]; then
  	      reason+=("$cert, used by $count jobs, has already expired")

  	  else
  	      reason+=("$cert, used by $count jobs, will expire on $( openssl x509 -in $cert -enddate -noout | cut -d= -f 2)")
  	  fi
        else
  	  reason+=("$cert, used by $count jobs, has expired and been deleted")
        fi
    fi
  done

  if [ -n "$reason" ]; then
      intro="Dear $( getent passwd $user | cut -d":" -f 5 ),

Your jobs on Hawk are using one or more expired or soon to be expired x509 grid proxy certificate files. This may cause issues if your jobs access private IGWN frame files, and they need to be restarted. The list of expired certificate files is:"

      reasons=""
    for reason in "${reason[@]}"; do
	reasons="$reasons
    $reason"
    done

    std_cert="/tmp/x509up_u$( id -u $user )"
    
    solution="
To renew your certificate files run
    
    unset X509_USER_PROXY
    ligo-proxy-init $user
"
    for cert in $certs; do
      if [ "$std_cert" != "$cert" ]; then
        solution+="    cp $std_cert $cert
"
      fi
    done

    optout="This reminder will run every day. To disable it run the following command on Hawk:

    touch /home/$user/.no_x509_warning_mail
"

    footer="If you have any problems or queries please email cardiff-igwn-cluster-help@cf.onmicrosoft.com"

    echo "$intro
$reasons
$solution
$optout
$footer" | mail -s "Expired on soon to be expired proxy in use on Cardiff Hawk cluster" -S "from=cardiff-igwn-cluster-help@cf.onmicrosoft.com" $user@ligo.org
  fi
done
