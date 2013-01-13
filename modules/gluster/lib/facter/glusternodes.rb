Facter.add("glusternodes") do
    # TODO: Ignore disconnected nodes and return only active ones.
    setcode do
        `/usr/sbin/gluster peer status|grep Hostname|head -n 1|cut -f2 -d ' '`.strip
    end
end
