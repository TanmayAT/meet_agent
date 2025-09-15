# below commands read env variables from dockerfile to create/update appropiate trunks in livekt cloud account
lk sip inbound create inbound-trunk.json
lk sip dispatch create dispatch-rule.json