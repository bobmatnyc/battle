#!/bin/zsh
cd /Users/masa/trusty-mpm-projects/bobmatnyc/battle/.claude/worktrees/agent-a3710adf3b45ab492
for s in little-round-top gergovia-recall concord-north-bridge hougoumont-north-gate pegasus-bridge hill-223-patrol; do
  echo "== $s"
  make headless-poc SCENARIO=$s > /tmp/t25/ctl-$s.log 2>&1
  echo "EXIT=$?"
  grep -o "Headless artifacts: .*" /tmp/t25/ctl-$s.log
  grep -o "'winner': '[a-z]*', 'turns': [0-9]*, 'events': [0-9]*" /tmp/t25/ctl-$s.log
done
