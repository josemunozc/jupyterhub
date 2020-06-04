#!/usr/bin/python
import time
import htcondor

MAX_NODES = 8
MAX_CORES = MAX_NODES*80

schedd = htcondor.Schedd()
idle_parallel_jobs = schedd.query(
    constraint='JobUniverse == 11 && JobStatus == 1',
    attr_list=["ClusterId", "Owner", "RequestCpus", "Requirements", "MinHosts"],
)


if not idle_parallel_jobs:
    print("No idle parallel jobs")
    exit()

total_idle_cores = sum(j["RequestCpus"] * j["MinHosts"] for j in idle_parallel_jobs)

print("Idle parallel jobs require {} cores".format(total_idle_cores))
for job in idle_parallel_jobs:
    print("* Job {ClusterId}: {Owner} {MinHosts} {RequestCpus}\n   {Requirements:.120}...".format(**job))
    print("")

running_parallel_jobs = schedd.query(
    constraint='JobUniverse == 11 && JobStatus == 2',
    attr_list=["ClusterId", "Owner", "RequestCpus", "Requirements", "MinHosts"],
)

total_cores = sum(j["RequestCpus"] * j["MinHosts"] for j in running_parallel_jobs)

print("Running parallel jobs using {} cores".format(total_cores))
for job in running_parallel_jobs:
    print("* Job {ClusterId}: {Owner} {MinHosts} {RequestCpus}\n   {Requirements:.120}...".format(**job))
    print("")

if total_cores < MAX_CORES:
    collector=htcondor.Collector()

    machines = {}
    nodes=collector.query(htcondor.AdTypes.Startd,
                          "PartitionableSlot == true && TotalCpus == 80 && TotalGPUs == 0 && NumDynamicSlots > 4",
                          ["Machine", "Cpus", "ChildCpus", "MyAddress"])


    # Order availale nodes by free CPUs and how many jobs are running
    # More jobs mean they have lower CPU requirements so they can easily move elsewhere
    nodes.sort(key=lambda x: 2*x["Cpus"] + len(x["ChildCpus"]), reverse=True)

    nodes_required = min(total_idle_cores,MAX_CORES-total_cores)/80

    print("Nodes required: %s" % (nodes_required,))

    nodes_to_drain = nodes[:nodes_required]
    print("Starting to drain nodes:")
    for node in nodes_to_drain:
        startd = htcondor.Startd(node)
        drainJob = startd.drainJobs()
        print("Issued drain to node: %s" % (node["Machine"],))

    ## WAIT FOR DRAINING
    nodes_to_drain_simple = [n["Machine"] for n in nodes_to_drain]
    while nodes_to_drain_simple:
        time.sleep(60)
        nodes_list = ", ".join('"%s"' % (n,) for n in nodes_to_drain_simple)
        print("Waiting for nodes: %s" % (nodes_list,))
        nodes=collector.query(htcondor.AdTypes.Startd,
                              'member(Machine,{%s}) && '
                              'PartitionableSlot == true && '
                              'NumDynamicSlots == 0' % (nodes_list,),
                              ["Machine", "MyAddress"])

        if len(nodes) >= 2:
            for node in nodes[:2]:
                print("Cancelling drain on node: %s" % (node["Machine"],))
                startd = htcondor.Startd(node)
                startd.cancelDrainJobs()
                nodes_to_drain_simple.remove(node["machine"])

    print("All finished")
