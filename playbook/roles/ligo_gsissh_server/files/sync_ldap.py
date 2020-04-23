#!/opt/ligo_scw_sync/bin/python
import sys
import ldap3
import argparse
import logging
from pprint import pformat

EXIT_LDAP_ERROR=1
#EXIT_PROGRAM_ERROR=2

LIGO_SERVER = 'ldaps://ldap.ligo.org'
LIGO_USER = None
LIGO_PASSWORD = None
LIGO_USER_TREE = 'ou=people,dc=ligo,dc=org'
LIGO_USER_QUERY = '(&(objectclass=person)(objectclass=posixAccount)(isMemberOf=Communities:LSCVirgoLIGOGroupMembers)(isMemberOf=Communities:LVC:LSC:LDG:CDF:LDGCDFUsers))'
LIGO_USER_ATTRIBUTES = ['uid',
                     'cn',
                     'sn',
                     'givenName',
                     'employeeNumber',
                     'sshPublicKey',
                     'loginShell',
                     'mail',
                     'homeDirectory',
]

SCW_SERVER = 'ldaps://chldap.hawk.supercomputingwales.ac.uk'
#SCW_SERVER = 'ldaps://csn2.hawk.supercomputingwales.ac.uk
SCW_USER = None
SCW_PASSWORD = None
SCW_LIGO_CN = 'LIGO'
SCW_LIGO_OU= 'ou={},ou=Institutions'.format(SCW_LIGO_CN)
SCW_USER_TREE = '{},ou=Users,dc=supercomputingwales,dc=ac,dc=uk'.format(SCW_LIGO_OU)
SCW_USER_QUERY = '(&(objectclass=inetOrgPerson)(objectclass=posixAccount))'

SCW_USER_ATTRIBUTES = ['uid',
                       'cn',
                       'sn',
                       'objectClass',
                       'givenName',
                       'displayName',
                       #'sshPublicKey', Currently unsupported
                       'loginShell',
                       'mail',
                       'homeDirectory',
                       'uidNumber',
                       'gidNumber',
]

SCW_USER_PROTECTED_ATTRIBUTES = set(['uid', 'cn'])

SCW_USER_OBJECT_CLASSES = ['inetOrgPerson', 'posixAccount']
SCW_USER_DN = "cn={{cn}},{}".format(SCW_USER_TREE)

SCW_GROUP_OBJECT_CLASSES = ['posixGroup']
SCW_PRIVATE_GROUP_DN = "cn={{cn}},{},ou=PrivateGroups,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk".format(SCW_LIGO_OU)

SCW_LIGO_GROUPS = [
    'cn={},ou=Institutions,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk'.format(SCW_LIGO_CN),
    #'cn=scw1158,ou=Category3,ou=Projects,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk',
]

SCW_UID_OFFSET = 10**8
def map_uid_number(entry):
    if hasattr(entry, 'employeeNumber'):
        return int(entry.employeeNumber.value) + SCW_UID_OFFSET
    return int(entry['employeeNumber']) + SCW_UID_OFFSET

def get_value(entry, key):
    # Used to apply attribute map using simple key or function
    try:
        if callable(key):
            return key(entry)
        elif hasattr(entry[key], 'value'):
            return entry[key].value
    except KeyError:
        pass
    return entry.get(key)

# Attribute key or function taking ligo entry as only argument
LIGO_PRIMARY_KEY = map_uid_number
SCW_PRIMARY_KEY = "uidNumber"

# Format is 'scwKey' : 'ligoKey' or function taking ligo entry as only argument
ATTRIBUTE_MAP = {
    'sn' : 'sn',
    'givenName' : 'givenName',
    'displayName': 'cn',
    'homeDirectory': 'homeDirectory',
    'loginShell': 'loginShell',
    'mail': 'mail',
    'uid': 'uid',
    'cn': 'uid',
    #'sshPublicKey': 'sshPublicKey', Currently unsupported
    'uidNumber': map_uid_number,
    'gidNumber' : map_uid_number,
    'objectClass' : lambda x: SCW_USER_OBJECT_CLASSES if (int(get_value(x,'employeeNumber')) < 39990) else ['posixAccount', 'account']
    #'memberOf' : lambda x: 'cn=HAWK,ou=Systems,ou=Acess,ou=Groups',
}

try:
    from local_settings import *
except ImportError:
    print("No local settings.py file")

def get_ldap_entries(server_url,
                     username,
                     password,
                     tree,
                     query,
                     attributes,
                     primary_key,
                     mock=False):

    server = ldap3.Server(server_url, get_info=ldap3.ALL)
    if mock:
        conn = ldap3.Connection(server, username, password, auto_bind=True, client_strategy=ldap3.MOCK_SYNC)
        conn.bind()
        if server_url == LIGO_SERVER:
            conn.strategy.add_entry('employeeNumber=3101,ou=people,dc=ligo,dc=org',
                                    {'objectClass' : ['posixAccount', 'person', 'inetOrgPerson'],
                                     'cn' : 'Paul Douglas Hopkins',
                                     'employeeNumber' : '3101',
                                     'givenName' : 'Paul',
                                     'homeDirectory' : '/home/paul.hopkins',
                                     'loginShell' : '/bin/bash',
                                     'mail' : 'paul.hopkins@ligo.org',
                                     'sn' : 'Hopkins',
                                     'sshPublicKey' : ['ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCskE9mwikPIZAEyhFeA0CfQDdSk+UzwhD/C1pW00XINJWlzmbtgR5KpZwBwGQmPORhupsKuEbP/Z7LCJ72N6lJ7f6BNxINGNHzJTyyQFOZcIq46thM6HRMzequCWfaJhTrL5Qo76oTCZ2GZfpoh53GrgAQUKefvhBBnD/kBjt6VfSa5hw1aTLpedmy9nPcS/pZCdQWoA66W04OAt+ohDJnBl6JHcCps1l25RMm6Rd+WeMKESJljFo1FYRW+MQA5AiQMh1Qoyr9FkERmv2LM+ngTWi0Op9iTJYh/E1jFemZSgS9JSgkG76AQiY3G4bCcuBoPENCdoQbu10Evlig24hF paul.lonnkvist.hopkins@gmail.com',
                                                       'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA/gfQ9TCXv2VaFGsSoHRiKfzdj9ySvr1AViibAwsgt4KHl2HaqOUCNcwEJoe6DAn8eFI11ylE8TmMUMUTLjKbh4YUTxe97N8PFJKJbJRtMbwGy8CWyDUHixBoBmIfrOG3XMKQ/fOsolYvB8MuLY7UaZuAhDj7NFgCNe9CuIBF4ndlAAL58L19/kWbFTJlUoCVg4AXLUT2eZSHmhzWQ7Qy22x6OiTbczyCYTAkVqRJEfF+XWWJQD+Os1EpezvA+L7XplO76SIuca5Z6w29Hhe/Iyd8qi0WUUrb30yyVzo5fnE/3AUkEokF1ay378nTEYSbi9G2JcErEw106h30ZHiwZOQX6BwhHNpL3QUXS767px9Hz1l3WOs3eWf0t6qHDplksaJLaAA57RrQwQxrPZoVBvRxS8WIV6WUTC+pT9WtMwjbKNhdMS+hCnGW6+mAQwSAon2L1fD3n/3JI1kFkqWPwi+DakPEUBC9b6RuQ+R8T9DgF4TRRVOZvlyKy8goPgHJCQHdc+qgVrjGHy393uv7Vqo8osM/c9nMebnybf8sXt2NsO/O8L2N3PGSv0bOb/wCpntNwzDwDlZYygrByzqnjoPH2JdC5O7UpBQikc6htPwRvBNRcBQXyQ+JrYYuHRXwAfDlDLWaPT05eN6/lleSAWmRaEiNN21AbA+TdVkqtw== paul.hopkins@ligo.org'],
                                     'uid' : 'paul.hopkins'
                                    })
            conn.strategy.add_entry('employeeNumber=3000,ou=people,dc=ligo,dc=org',
                                    {'objectClass' : ['posixAccount', 'person', 'inetOrgPerson'],
                                     'cn' : 'Bob Thistle',
                                     'employeeNumber' : '3000',
                                     'givenName' : 'Bob',
                                     'homeDirectory' : '/home/bob.thistle',
                                     'loginShell' : '/bin/bash',
                                     'mail' : 'bob.thistle@ligo.org',
                                     'sn' : 'Thistle',
                                     'sshPublicKey' : ['ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCskE9mwikPIZAEyhFeA0CfQDdSk+UzwhD/C1pW00XINJWlzmbtgR5KpZwBwGQmPORhupsKuEbP/Z7LCJ72N6lJ7f6BNxINGNHzJTyyQFOZcIq46thM6HRMzequCWfaJhTrL5Qo76oTCZ2GZfpoh53GrgAQUKefvhBBnD/kBjt6VfSa5hw1aTLpedmy9nPcS/pZCdQWoA66W04OAt+ohDJnBl6JHcCps1l25RMm6Rd+WeMKESJljFo1FYRW+MQA5AiQMh1Qoyr9FkERmv2LM+ngTWi0Op9iTJYh/E1jFemZSgS9JSgkG76AQiY3G4bCcuBoPENCdoQbu10Evlig24hF paul.lonnkvist.hopkins@gmail.com',
                                                       'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA/gfQ9TCXv2VaFGsSoHRiKfzdj9ySvr1AViibAwsgt4KHl2HaqOUCNcwEJoe6DAn8eFI11ylE8TmMUMUTLjKbh4YUTxe97N8PFJKJbJRtMbwGy8CWyDUHixBoBmIfrOG3XMKQ/fOsolYvB8MuLY7UaZuAhDj7NFgCNe9CuIBF4ndlAAL58L19/kWbFTJlUoCVg4AXLUT2eZSHmhzWQ7Qy22x6OiTbczyCYTAkVqRJEfF+XWWJQD+Os1EpezvA+L7XplO76SIuca5Z6w29Hhe/Iyd8qi0WUUrb30yyVzo5fnE/3AUkEokF1ay378nTEYSbi9G2JcErEw106h30ZHiwZOQX6BwhHNpL3QUXS767px9Hz1l3WOs3eWf0t6qHDplksaJLaAA57RrQwQxrPZoVBvRxS8WIV6WUTC+pT9WtMwjbKNhdMS+hCnGW6+mAQwSAon2L1fD3n/3JI1kFkqWPwi+DakPEUBC9b6RuQ+R8T9DgF4TRRVOZvlyKy8goPgHJCQHdc+qgVrjGHy393uv7Vqo8osM/c9nMebnybf8sXt2NsO/O8L2N3PGSv0bOb/wCpntNwzDwDlZYygrByzqnjoPH2JdC5O7UpBQikc6htPwRvBNRcBQXyQ+JrYYuHRXwAfDlDLWaPT05eN6/lleSAWmRaEiNN21AbA+TdVkqtw== paul.hopkins@ligo.org'],
                                     'uid' : 'bob.thistle'
                                    })
        else:
            conn.strategy.add_entry('cn=paul.hopkins,ou=LIGO,ou=Institutions,ou=Users,dc=supercomputingwales,dc=ac,dc=uk',
                                    {'cn' : 'paul.hopkins',
                                     'sn' : 'Hopkins',
                                     'gidNumber' : '100003101',
                                     'givenName' : 'Paul',
                                     'displayName' : 'Paul Douglas Hopkins',
                                     'homeDirectory' : '/home/paul.hopkins',
                                     'loginShell' : '/bin/bash',
                                     'objectClass' : ['inetOrgPerson', 'posixAccount'],
                                     'mail' : 'paul.hopkins@ligo.org',
                                     'uid' : 'paul.hopkins',
                                     'uidNumber' : '100003101',
                                     })
            conn.strategy.add_entry('cn=LIGO,ou=Institutions,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk',
                                    {'objectClass' : ['posixGroup']})
            conn.strategy.add_entry('cn=scw1158,ou=Category3,ou=Projects,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk',
                                    {'objectClass' : ['posixGroup']})

    else:
        conn = ldap3.Connection(server, username, password, auto_bind=True)


    conn.search(tree, query, attributes=attributes)
    entries = dict((str(get_value(entry, primary_key)), entry) for entry in conn.entries)

    return conn, entries

def as_list(i):
    return i if isinstance(i, list) else [i]

def should_force(force, private_key, new_entry, criteria):
    if (force
        or private_key in criteria
        or new_entry.get('cn') in criteria
        or "ALL" in criteria):
        return True

class LDAPSyncer(object):
    def __init__(self, scw_conn, scw_entries, args):
        self.scw_conn = scw_conn
        self.scw_entries = scw_entries
        self.args = args
        if args.dry_run:
            logging.info("Dry-run: Will not make changes")

    def check_result(self):
        if self.scw_conn.result.get('result'):
            logging.error("Fatal error: {}: {}".format(
                self.scw_conn.result.get('description', '??'),
                self.scw_conn.result.get('message', '??')
            ))
            sys.exit(EXIT_LDAP_ERROR)

    def add_user(self, primary_key, new_entry, force=False):
        logging.info("Adding user %s (%s)", primary_key, new_entry['uid'])

        user_dn = SCW_USER_DN.format(**new_entry)
        logging.debug("Creating entry %s: %s", user_dn, pformat(new_entry))
        if not self.args.dry_run:
            self.scw_conn.add(user_dn,
                              new_entry['objectClass'],
                              new_entry)
            self.check_result()

        private_group_dn = SCW_PRIVATE_GROUP_DN.format(**new_entry)
        private_group = {'cn' : new_entry['cn'],
                         'memberUid' : new_entry['uid'],
                         'gidNumber' : new_entry['gidNumber']}

        logging.debug("Creating private group entry %s: %s", private_group_dn, pformat(private_group))
        if not self.args.dry_run:
            self.scw_conn.add(private_group_dn,
                              SCW_GROUP_OBJECT_CLASSES,
                              private_group)
            self.check_result()

        for lsc_group_dn in SCW_LIGO_GROUPS:
            logging.debug("Adding user to LIGO group %s", lsc_group_dn)
            if not self.args.dry_run:
                self.scw_conn.modify(lsc_group_dn,
                                     {'memberUid' : (ldap3.MODIFY_ADD, new_entry['cn']),
                                  })
                self.check_result()

    def compare_user(self, primary_key, new_entry, force=False):
        logging.debug("Comparing entry %s (%s)", primary_key, new_entry['uid'])
        cur_entry = self.scw_entries[primary_key]
        logging.debug("Current entry %s\n", pformat(cur_entry))

        diff_items = {}
        for key in SCW_USER_ATTRIBUTES:
            cur_value = set()
            if key in cur_entry.entry_attributes:
                cur_value = set(as_list(cur_entry[key].value))

            new_value = set()
            if key in new_entry:
                new_value = set(as_list(new_entry.get(key)))

            if cur_value != new_value:
                logging.debug("Key %s differs %s -> %s", key, cur_value, new_value)
                diff_items[key] = [(ldap3.MODIFY_REPLACE, list(new_value))]

        if not diff_items:
            logging.debug("No changes required")
            return

        dn = cur_entry.entry_dn

        if SCW_USER_PROTECTED_ATTRIBUTES.intersection(diff_items.keys()):
            if not should_force(force, primary_key, new_entry, args.protected):
                logging.warn("Change in protected values for user %s (%s->%s), force required.",
                             primary_key,
                             cur_entry['cn'].value,
                             new_entry['cn'])
                return
            logging.info("Change in protected values for user forced")
            # MORE CHANGES NEED TO GO IN HERE
            # Private Group:
            #   MOVE cn=old.cn,ou=LIGO,ou=Institutions,ou=PrivateGroups,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk-> and
            #   CHANGE memberUid: old.cn -> new.cn
            # LIGO Group: cn=LIGO,ou=Institutions,ou=Groups,dc=supercomputingwales,dc=ac,dc=uk
            #   Remove MemberUid: old.cn
            #   Add MemberUid: new.cn
            # Check whether we need to invalidate sss_cache (-u old.cn, or -u new.cn)
            # TODO
            cn_changes = "cn={}".format(new_entry['cn'])
            logging.info("Moving user %s: %s", dn, cn_changes)
            if not self.args.dry_run:
                pass
                #self.scw_conn.modify_dn(dn, cn_changes)
                #self.check_result()

            cur_private_group_dn = SCW_PRIVATE_GROUP_DN.format(cn=cur_entry['cn'].value)
            logging.info("Moving private group %s: %s", cur_private_group_dn, cn_changes)
            if not self.args.dry_run:
                pass
                #self.scw_conn.modify_dn(cur_private_group_dn, cn_changes)
                #self.check_result()

            group_changes = {'memberUid' : [(ldap3.MODIFY_ADD, new_entry['cn']),
                                            (ldap3.MODIFY_DELETE, cur_entry['cn'].value)]
                         }
            for lsc_group_dn in SCW_LIGO_GROUPS:
                logging.info("Updating LIGO group %s: %s", lsc_group_dn, group_changes)
                if not self.args.dry_run:
                    pass
                    #self.scw_conn.modify(lsc_group_dn, group_changes)
                    #self.check_result()

            logging.error("""Manual steps required:
                Move /home and /scatch directories:
                cd /home
                mv /nfshome/store01/users/hendrick.mayer /nfshome/store01/users/hendrik.mayer
                ln -fs /nfshome/store01/users/hendrik.mayer
                ln -fs /nfshome/store01/users/hendrik.mayer hendrick.mayer
                cd /scratch
                mv hendrick.mayer hendrik.mayer
                Check whether we need to invalidate sss_cache (-u old.cn, or -u new.cn)""")
            
            dn = SCW_USER_DN.format(**new_entry)
        logging.info("Applying changes to %s\n %s", dn, pformat(diff_items))
        if not self.args.dry_run:
            self.scw_conn.modify(dn,
                                 diff_items)
            self.check_result()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose",
                        action="count", default=0,
                        help="increase output verbosity")
    parser.add_argument("-m", "--mock",
                        action='store_true',
                        help="Test with mock data")
    parser.add_argument("-n", "--dry-run",
                        action='store_true',
                        help="Do not make changes")
    parser.add_argument("-p", "--protected",
                        action='append',
                        default=[],
                        help="Modify protected attributes for user")
    args = parser.parse_args()

    logging.basicConfig(level=(3-args.verbose)*10)

    if args.mock:
        # This is the real query we want
        LIGO_USER_QUERY = '(&(objectclass=inetOrgPerson)(objectclass=posixAccount))'


    ligo_conn, ligo_entries = get_ldap_entries(LIGO_SERVER,
                                               LIGO_USER,
                                               LIGO_PASSWORD,
                                               LIGO_USER_TREE,
                                               LIGO_USER_QUERY,
                                               LIGO_USER_ATTRIBUTES,
                                               LIGO_PRIMARY_KEY,
                                               args.mock)
    # HARD CODE extra fields:
#    ligo_extra = [{
#        'uid' : 'cvmfs',
#        'cn': 'CernVM-FS service account',
#        'employeeNumber' : 40000,
#        'homeDirectory': '/var/lib/cvmfs',
#        'loginShell': '/sbin/nologin',
#        'uid': u'cvmfs',
#    }]
#    for entry in ligo_extra:
#        ligo_entries[str(get_value(entry, LIGO_PRIMARY_KEY))] = entry

    scw_conn, scw_entries = get_ldap_entries(SCW_SERVER,
                                             SCW_USER,
                                             SCW_PASSWORD,
                                             SCW_USER_TREE,
                                             SCW_USER_QUERY,
                                             SCW_USER_ATTRIBUTES,
                                             SCW_PRIMARY_KEY,
                                             args.mock)

    syncer = LDAPSyncer(scw_conn, scw_entries, args)

    logging.debug("All Ligo Entries: %s", pformat(ligo_entries))
    logging.debug("All Scw Entries: %s", pformat(scw_entries))

    for primary_key, entry in ligo_entries.items():
        logging.debug("Considering entry key=%s:\n %s\n", primary_key, pformat(entry))

        # Generate how entry should look
        new_entry = {}
        for scw_attr, src_attr in ATTRIBUTE_MAP.items():
            new_value = get_value(entry, src_attr)
            if new_value:
                new_entry[scw_attr] = new_value

        logging.debug("Converted entry key=%s:\n %s\n", primary_key, pformat(new_entry))

        if primary_key in scw_entries:
            logging.debug("Entry %s found in destination", primary_key)
            # Case (2)
            syncer.compare_user(primary_key, new_entry)
        else:
            logging.debug("Entry %s not found in destination", primary_key)
            # Case (1)
            syncer.add_user(primary_key, new_entry)

    for primary_key, entry in scw_entries.items():
        # Case (0)
        if entry['loginShell'] in ['/usr/sbin/nologin', '/sbin/nologin']:
            continue

        # Case (3)
        if primary_key not in ligo_entries:
            diff_items = {'loginShell' : [(ldap3.MODIFY_REPLACE, ['/usr/sbin/nologin'])]}
            logging.info("Applying changes to %s\n %s", entry.entry_dn, pformat(diff_items))

            syncer.scw_conn.modify(entry.entry_dn, diff_items)
            syncer.check_result()

# TEST MATRIX

# LIGO \ SCW  |  NOT PRESENT  | Present (Active)  | Present (Inactive)
# ----------------------------------------------------------------------------
# NOT PRESENT | Nothing (-1)  | Deactivate (3)    | Nothing (0)
# -----------------------------------------------------------------------------
# PRESENT     | Add user (1)  | Compare and Modify, and if necessary active (2)
