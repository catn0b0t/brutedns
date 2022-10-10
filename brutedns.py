import argparse
import json
import random
import string
import progressbar
import dns.resolver
import socket

from dns.rdatatype import CNAME


def enumerateDomain(domain, nameservers):
    widgets = [' [',
               progressbar.Timer(format='elapsed time: %(elapsed)s'),
               '] ',
               progressbar.Bar('*'), ' (',
               progressbar.ETA(), ') ',
               ]
    resolver = dns.resolver.Resolver(configure=False)
    possibilities = open('wordlist.txt').readlines()
    nsHosts = []
    for ns in nameservers:
        nsHosts.append(socket.gethostbyname(ns))
    resolver.nameservers = nsHosts
    hostnames = []
    try:
        res = resolver.resolve(domain)
        hostnames.append(domain)
    except:
        pass
    bar = progressbar.ProgressBar(max_value=len(possibilities),
                                  widgets=widgets).start()
    counter = 0
    for possibility in possibilities:
        possibility = ''.join(ch for ch in possibility if ch.isalnum())
        hostname = possibility + '.' + domain
        try:
            # First try to get A records
            resolver.resolve(hostname)
            hostnames.append(hostname)
        except Exception as e:
            # If no A record, try CNAME record
            try:
                resolver.resolve(hostname, CNAME)
                hostnames.append(hostname)
            except Exception as e:
                pass
        counter = counter + 1
        bar.update(counter)
    return hostnames


def bruteDomain(domain):
    result = {"domain": domain, "hostnames": []}
    result.update(getSOA(domain))
    result["nameservers"] = getNS(domain, result.get('primaryNameServer'))
    result["isWildcardDomain"] = verifyWildcard(domain)
    result["hostnames"] = enumerateDomain(result["domain"], result["nameservers"])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", help="The root of the domain to enumerate, ie. example.com")
    args = parser.parse_args()
    print(json.dumps(bruteDomain(args.domain), indent=2))


def verifyWildcard(domain):
    # Generates a random string and does a lookup using this string as a hostname in the domain.
    # If it succeeds and returns True, this means the domain implements a wildcard
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8"]
    rnd = ''.join(random.choice(string.ascii_lowercase) for i in range(24)) + '.' + domain
    try:
        resolver.resolve(rnd)
        return True
    except Exception as e:
        return False


def getNS(domain, primaryNameServer):
    # Returns a list of NS hostnames for the domain
    resolver = dns.resolver.Resolver(configure=False)
    if primaryNameServer:
        resolver.nameservers = [socket.gethostbyname(primaryNameServer)]
    ns = []
    for namesrv in resolver.resolve(domain, "NS"):
        ns.append(str(namesrv).strip('.'))
    return ns


def getSOA(domain):
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8"]
    soa = resolver.resolve(domain, "SOA")
    s = {"primaryNameServer": str(soa[0].mname).strip('.')}
    labelcnt = 0
    email = str(soa[0].rname[0].decode("utf-8")).replace('\\.', '.') + "@"
    for label in soa[0].rname:
        if labelcnt != 0:
            email = email + str(label.decode("utf-8")) + '.'
        labelcnt = labelcnt + 1
    s['administrativeContact'] = email.strip('.')
    return s


if __name__ == '__main__':
    main()
