# TCP Offset Estimator

This tool estimates a **translation-only** TCP offset in the flange frame while the project is still using `tcp_offset = 0`.

Launch it with:

```bash
./scripts/run_estimate_tcp_offset.sh
```

Recommended workflow:

1. Keep the current project TCP offset at zero.
2. Move the robot to a view where the target point is visible.
3. Click a fixed point in the D405 image.
4. The tool freezes that point in the base frame using the current hand-eye result.
5. Manually drag the robot until the intended grasp center reaches the same physical point.
6. Press `Capture Sample`.
7. Repeat from several different poses.
8. Save the result and use the mean value as the next TCP offset candidate.

The saved YAML includes:

- the suggested `tcp_offset` as `[x, y, z, 0, 0, 0]`
- sample statistics
- every captured sample

Suggested first pass:

- capture at least 5 samples
- prefer visibly different wrist poses
- if the sample spread is large, redo the worst alignments instead of averaging noisy data

Keyboard shortcuts:

- `s`: capture sample
- `d`: delete last
- `c`: clear target
- `r`: reset session
- `w`: save YAML
