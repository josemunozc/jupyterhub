# kickstart template for Centos 7 on R640 for LIGO
# OS RAID disk is sda

# System authorization information
auth  --useshadow  --passalgo=sha512
# System bootloader configuration
ignoredisk --only-use=sda
bootloader --location=mbr --boot-drive=sda
# Partition clearing information
clearpart --all --initlabel --drives=sda
# Use text mode install
text
# Firewall configuration
firewall --enabled
#services
services --disabled=NetworkManager --enabled=network
# Run the Setup Agent on first boot
firstboot --disable
eula --agreed
# System keyboard
keyboard uk
# System language
lang en_GB
# Reboot after installation
reboot

#Network
network --bootproto=dhcp --device=em1
network --bootproto=dhcp --device=em2 --onboot=off --ipv6=auto
network --bootproto=dhcp --device=em3 --onboot=off --ipv6=auto
network --bootproto=dhcp --device=em4 --onboot=off --ipv6=auto
network --hostname stashcache.gravity.cf.ac.uk
#Root password
rootpw --iscrypted $6$0ukQ9mTza695qOrI$a8fxWpJldMdtjQ2qI/GYuei4ozfOPmKiujtqDQYD/20C5A0TTERs097eJjeJ26dxK/lPTogKowiClaxSc1Sxf0
# SELinux configuration
selinux --disabled
# Do not configure the X Window System
skipx
# System timezone
timezone  Europe/London
# Install OS instead of upgrade # NOTE USB INSTALL FROM SDC
install
harddrive --partition=sdc1 --dir=/
# Clear the Master Boot Record
zerombr
# Disk partitioning information
part /boot --asprimary --fstype="ext4" --ondisk=sda --size=1024
part pv.1 --fstype="lvmpv" --ondisk=sda --size=1 --grow
#create vg
volgroup centos_vg --pesize=4096 pv.1
#grow root to max size
logvol /  --fstype="xfs" --grow --size=1 --name=root --vgname=centos_vg

%packages 
@core
%end

%post
yum -y remove NetworkManager
useradd -d /etc/ansible -c "Ansible User" -U ansible -u 5000
gpasswd -a ansible wheel
echo "ansible ALL=(ALL)      NOPASSWD: ALL" >> /etc/sudoers
mkdir /etc/ansible/.ssh
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDRgzXkr7qrxfu0iRgWDgiXW562iUEvSTxWGNBQeY0SbF15LwjGt2s1utYkSLN0zVzbejL/SH7O4vcDjxdwlHJhcL0YdandX6DSTtQwnl4Vkg7TeZe8uXIZcgIFKviXg1iuoXQiKR7+wsmQElq+j+wxxMAgS4iTFP/qBejLPYZOV6Ldyo2h6IfSLthXBEsUe6tCDR0BSvvfGC+K4Ff3T8y6D+3E7LqsSvELV561bWUt9QsfxRn1YPlKaOB4VywBh02Ak5JNDUYbRh/9jEAF2LblfD0w21j8j78bvagqnj7Du8dML9gOgjBZ9ePEPeBE1I6UxFTZ7jimAGEqx5SCInX1 ansible@arccadeploy.cf.ac.uk" > /etc/ansible/.ssh/authorized_keys
%end
