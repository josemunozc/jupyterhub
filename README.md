# Instructions to deploy JupyterHub on a baremetal system.
Dependencies:
- git
- ansible


We need the [ansible posix ](https://github.com/ansible-collections/ansible.posix) to work
with firewalld. To install it run (after installing ansible):
```
ansible-galaxy collection install ansible.posix
```

To deploy run (as root):
```
ansible-playbook -i myhosts jhub.yml 
```

A few useful commands to check service status or if restart the service if necessary:
```
sudo systemctl stop jupyterhub.service
sudo systemctl start jupyterhub.service
sudo systemctl status jupyterhub.service
```
