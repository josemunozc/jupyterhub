#!/bin/sh

username=$1

[ "$username" == "" ] && exit

uid=`id -u $username 2>/dev/null`

if  [ $? -ne 0 ] || [ $uid -lt 10000000 ]; then
  exit
fi

filter="(&"
  filter+="(isMemberOf=Communities:LSCVirgoLIGOGroupMembers)"
  filter+="(isMemberOf=Communities:LVC:LSC:LDG:CDF:LDGCDFUsers)"
  filter+="(sshPublicKey=*)"
  filter+="(|"
    filter+="(x-LIGO-uid=$username*)"
    filter+="(x-LIGO-uid;x-ligo-ldg-cdf=*,$username*)"
filter+="))"

curl -s ldaps://ldap.ligo.org/ou=people,dc=ligo,dc=org?sshPublicKey?sub?$filter | grep "sshPublicKey: " | cut -d" " -f 2-

exit 0
