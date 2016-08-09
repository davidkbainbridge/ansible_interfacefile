# Ansible Network Interface File Module
This is an ansible module that can be used to manage the definitions in the linux
`/etc/network/interfaces` file. 

# How It Works
This module first parses the `/etc/network/interfaces` file and the evaluates the
ansible task specification to what exists in the file. When thre is a change the
module writes the updated file back to storage and return a changed status of `True.
If there is no change then the file is not written unless the `force` option is
set to True.

In addition to the states `present` and `absent`, the `state` attribute can also
be set to `query` to query the value of a given interface. If `query` is specified
then if the named interface exists the result of the task will be unchanged and the
result will contain the attribute `found` set to `true` and the attribtue `interface`
set to the value of the interface. If the named interface does not exist then the
result will be unchanged and the result wil container the attribute `found` set to
`false`.

If the file is written and comments in the existing file will be lost as comment
information is not maintained in the model of the file's information.

This module is written to attempt to work with all attributes that can be specified
in a generic fashion so to provide the most use without having "knowledge" of
every possible option. Specific attributes of interest are:

- **src** - the source interface file, defaults to `/etc/network/interfaces`
- **dest** - the file to write if required, default to src if not specified
- **state** - `present` if the specification must be in the file, `absent` if it shouldn't. Additionally the state can be `query` to query an interface specification from the file.
- **name** - name of the interface
- **auto** - should the interface be auto enabled
- **type** - type of the interface, defaults to `inet`
- **config** - how the interface is configured, defaults to `manual`
- **force** - for the file to be written, even if there is no change

When specifying the **address** attributes, you can either specify them individually,
i.e., `address`, `network`, and `netmask` or you can specify `address` in netmask
location with the IP address and the network bits, i.e. `192.168.42.31/24`.
