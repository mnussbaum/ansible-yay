# ansible-yay

An Ansible module for installing [AUR](https://aur.archlinux.org/) packages via
the [yay][yay] AUR helper.

This assumes your target node already has yay and its dependecies installed.

## Dependencies (Managed Node)

* [Arch Linux](https://www.archlinux.org/) (Obviously)
* [yay][yay]

## Installation

Install the collection from Ansible Galaxy:

    $ ansible-galaxy collection install mnussbaum.ansible_yay

Or install the latest development version straight from GitHub:

    $ ansible-galaxy collection install git+https://github.com/mnussbaum/ansible-yay.git

The module is then available under its fully qualified collection name,
`mnussbaum.ansible_yay.yay` (see Usage below).

## Usage

Pretty much identical to the [pacman module][pacman-mod]. Note that package
status, removal, the corresponding `pacman` commands are used (`-Q`, `-R`,
respectively).

### Options

| parameter    | required  | default | choices               | description                         |
|--------------|-----------|---------|-----------------------|-------------------------------------|
| name         | no        |         |                       | Name of the AUR package to install. |
| recurse      | no        | no      | yes/no                | Whether to recursively remove packages. See [pacman module docs][pacman-mod]. |
| state        | no        | no      | absent/present/latest | Whether the package needs to be installed or updated. |
| update_cache | no        | no      | yes/no                | Whether or not to refresh the master package lists. This can be run as part of a package installation or as a separate step. |
| upgrade      | no        | no      | yes/no                | Whether or not to upgrade the whole systemd. |

### Examples

```yaml
# Install package foo
- mnussbaum.ansible_yay.yay: name=foo state=present

# Ensure package fuzz is installed and up-to-date
- mnussbaum.ansible_yay.yay: name=fuzz state=latest

# Remove packages foo and bar
- mnussbaum.ansible_yay.yay: name=foo,bar state=absent

# Recursively remove package baz
- mnussbaum.ansible_yay.yay: name=baz state=absent recurse=yes

# Effectively run yay -Syu
- mnussbaum.ansible_yay.yay: update_cache=yes upgrade=yes
```

[yay]: https://github.com/Jguer/yay
[pacman-mod]: http://docs.ansible.com/pacman_module.html
