class gluster::server {
    include apt

    file {
        '/var/cache/puppet':
            ensure => directory,
            owner  => root,
            group  => root;
        '/var/cache/puppet/packages':
            ensure => directory,
            owner  => root,
            group  => root,
            require => File['/var/cache/puppet'];
        '/var/cache/puppet/packages/glusterfs_3.3.0-1_amd64.deb':
            ensure  => present,
            source  => 'puppet:///modules/gluster/glusterfs_3.3.0-1_amd64.deb',
            owner   => root,
            group   => root,
            notify  => Exec['create_repo'],
            require => File['/var/cache/puppet/packages'];
        '/srv/archive':
            ensure => directory,
            owner  => root,
            group  => root,
            mode   => 755;
        '/srv/archive/conf':
            ensure  => directory,
            owner   => root,
            group   => root,
            mode    => 755,
            require => File['/srv/archive'];
        '/srv/archive/conf/distributions':
            ensure => present,
            owner  => root,
            group  => root,
            mode   => 644,
            source => 'puppet:///modules/gluster/apt/distributions',
            require => File['/srv/archive/conf'];
        '/srv/archive/conf/options':
            ensure => present,
            owner  => root,
            group  => root,
            mode   => 644,
            source => 'puppet:///modules/gluster/apt/options',
            require => File['/srv/archive/conf'];
        '/srv/gluster':
            ensure => directory,
            owner  => root,
            group  => root,
            mode   => 755;
        '/usr/local/bin/gluster-fencer':
            ensure => present,
            owner => root,
            group => root,
            mode => 755,
            source => 'puppet:///modules/gluster/firewall/gluster-fencer.py',
            require => Package['python-netfilter'];
    }



    exec {
        'create_repo':
            creates => '/srv/archive/pool',
            command => 'reprepro includedeb precise /var/cache/puppet/packages/glusterfs_3.3.0-1_amd64.deb',
            notify  => Exec['apt-get_update'],
            cwd     => '/srv/archive/',
            require => [
                File[
                    '/var/cache/puppet/packages/glusterfs_3.3.0-1_amd64.deb',
                    '/srv/archive/conf/options', '/srv/archive/conf/distributions'
                ],
                Package['reprepro']
            ];
        'mkfs_ext4':
            command => 'mkfs.ext4 /dev/xvdh',
            unless  => 'file -s /dev/xvdh |grep ext4',
            require => Package['e2fsprogs'];
        #'create_gluster_volume':
        #    command => 'gluster volume create test replica 2 transport tcp ',
        #    unless  => 'file -s /dev/xvdh |grep ext4',
        #    require => Package['e2fsprogs'];


    }

    mount {
        '/srv/gluster':
            atboot => true,
            device => '/dev/xvdh',
            ensure => mounted,
            name => '/srv/gluster',
            fstype => 'ext4',
            options => 'auto,noatime',
            require => [Exec['mkfs_ext4'], File['/srv/gluster']]
    }

    apt::sources_list {
        'gluster':
            ensure  => present,
            content => 'deb file:///srv/archive precise main',
            notify  => Exec['apt-get_update'],
            require => Exec['create_repo'];
    }

    package {
        ['e2fsprogs',
         'reprepro',
         'python-netfilter']:
            ensure => present;
        'glusterfs':
            ensure  => '3.3.0-1', # This forces the installation even without
                                  # a valid archive signature.
            require => Exec['apt-get_update'];
    }

    service {
        'glusterd':
            ensure  => running,
            enable  => true,
            require => Package['glusterfs'];

    }

}

class gluster::server::master {
    Exec <<| tag == 'gluster_probe' |>>

    exec {
        'gluster_create_volume':
            command => "gluster volume create gv0 replica 2 ${fqdn}:/srv/gluster ${glusternodes}:/srv/gluster",
            onlyif => "test -n $glusternodes",
            unless => "gluster volume info gv0",
            require => Exec["gluster_probe_${glusternodes}"];
        'gluster_start_volume':
            command => "gluster volume start gv0",
            unless => "gluster volume info gv0 | grep 'Status: Started'",
            require => Exec["gluster_create_volume"];
    }

    @@mount {
        '/mnt':
            atboot => true,
            device => "$fqdn:/gv0",
            ensure => mounted,
            name => '/mnt',
            fstype => 'glusterfs',
            options => 'defaults,_netdev',
            tag => 'client_mount';
    }
}

class gluster::server::slave {
    @@exec {
        "gluster_probe_${fqdn}":
            command => "gluster peer probe $fqdn",
            require => [
                Package['glusterfs']
            ],
            tag => 'gluster_probe';
    }

}

class gluster::client {

    Mount <<| tag == 'client_mount' |>>
}
