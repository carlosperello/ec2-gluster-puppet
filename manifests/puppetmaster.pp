node default {
    class {
        "puppet::master":
            node_bucket => "https://cpm-puppet-nodes-1.s3.amazonaws.com";
    }
}
