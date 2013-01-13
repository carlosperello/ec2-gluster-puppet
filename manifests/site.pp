node default {

  ssh_authorized_key {
    'carlos':
      key => 'AAAAB3NzaC1kc3MAAACBAPRpIa6PlQ4o48HQ0j1jTlwmBDZQ7gQexmZlaO+bh3HBHjdQB1JNYlE8SsXkXlL1e7W6YcU8bRdpgk5Ez1URsj6T4wMGd2+W+voHnYj0mj1eUoA3KBnXIdquklHrvTUrFinF2Lq54/SRd8TzVAFkHoqcgVDv1iYFzAwWjpB+QBqbAAAAFQCdFNAIOFJRI1vYEuNjM1Sim02aBwAAAIEAm05Y5kLH+kqOp1Tf4DUc8pg4xq6Vj7O7r5TuG2WbgGgBsBRjeMYWvszlob/1v2AMbgcZ+thp6WzvdXAjB0AlxzTWc6SU9tbQATIZpf6Lal07afuKNIMBQ1k8AuaU81UABq/ZD9LW80XoDCdoMTWqdFOx9q8C7vjSEM+9FLbnOu4AAACBAM30F0MC/akkCOPGRYPnCgBweLdB5pu2jvG1wNK9f1ev8ieiZ3LUX1AqyVcMdPj2AcypjY/vdr1xRNrH2jkXNuJJqk5/35NlkD/zGS0Euo0DfHmvAW7B56NCrujnNExE0wvoL//YzNLGMaTimO6IuJxbMehw4iw0kL5LREVR4k01',
      user => 'ubuntu',
      type => 'ssh-dss';
  }
}

# General settings for standard types
Exec { path => "/usr/local/bin:/bin:/sbin:/usr/bin:/usr/sbin" }
