#############################################################################
# worker.tcl  —  evaluation worker loop that runs inside an open Capture session
#
# How to enable it (only needs to be done once per Capture session):
#   1. Start D:\orcad\tools\bin\Capture.exe (log in if first time).
#   2. Open the Tcl Command Window (Window -> Command Window).
#   3. Paste:
#        source D:/localwork/orcad/tasks/_common/worker.tcl
#        ::engiworld::worker::start
#
# Once running, the worker polls  D:/localwork/orcad/tasks/_worker_queue  every
# 2 seconds.  Any *.tcl file found there is sourced (inside its own namespace
# for isolation) and then moved to the ./done/ subdir.  The sourced script is
# responsible for writing its verdict JSON back to disk at a path of its own
# choosing (eval.py knows where to look).
#
# The worker is deliberately minimal:  no network, no external exec, just
# `source` of user-supplied Tcl in the running Capture process.  The caller
# (eval.py) should feed it only trusted scripts it has written itself.
#############################################################################

namespace eval ::engiworld::worker {
    variable queue_dir "D:/localwork/orcad/tasks/_worker_queue"
    variable done_dir  "D:/localwork/orcad/tasks/_worker_queue/done"
    variable running   0
    variable tick_ms   1500
}

proc ::engiworld::worker::start {} {
    variable running
    if {$running} {
        puts "\[engiworld worker] already running"
        return
    }
    variable queue_dir
    variable done_dir
    file mkdir $queue_dir
    file mkdir $done_dir
    set running 1
    puts "\[engiworld worker] started; watching $queue_dir"
    poll
}

proc ::engiworld::worker::stop {} {
    variable running
    set running 0
    puts "\[engiworld worker] stop requested"
}

proc ::engiworld::worker::poll {} {
    variable running
    variable tick_ms
    variable queue_dir
    variable done_dir
    if {!$running} { return }

    set jobs [lsort [glob -nocomplain -type f [file join $queue_dir "*.tcl"]]]
    foreach job $jobs {
        set name [file tail $job]
        set stamp [clock format [clock seconds] -format "%H:%M:%S"]
        puts "\[engiworld worker] \[$stamp] running: $name"
        set rc [catch {
            uplevel #0 [list source $job]
        } err]
        if {$rc} {
            puts "\[engiworld worker]   ERROR in $name: $err"
            # Write an .err file next to the job for the caller to discover.
            set errf [string map {".tcl" ".err"} [file join $done_dir $name]]
            set fd [open $errf w]
            puts $fd $err
            close $fd
        }
        # Move the job to done/.
        set dest [file join $done_dir $name]
        catch { file delete -force $dest }
        catch { file rename -force $job $dest }
    }
    after $tick_ms [list ::engiworld::worker::poll]
}

# If this file is re-sourced, provide convenience.
if {[info exists ::engiworld::worker::running] && !$::engiworld::worker::running} {
    puts "\[engiworld worker] loaded. Call ::engiworld::worker::start to begin."
}
