# multi_full pooled model — per-symbol error

## Setup

- Model: `regime_model_v2_multi_full.pkl` (pooled BTC/ETH/BNB/SOL/XRP)
- Features: `prepare_features_v2` + `FEATURE_COLS` from `train_model_v2_multi.py`
- Labels: `label_data_3class_quantile(look_forward=24, quantile=0.6)`
- **Training does NOT include `symbol` as a feature** (only FEATURE_COLS).
- Gated hit rate filter: pred∈{0,2}, conf≥0.85, ADX≥35.0, |DI_diff|≥15.0, DI agrees with side (+DI>-DI for pred=2; -DI>+DI for pred=0).
- Usable rows: after feature dropna + drop last 24 bars without future labels.

## BTC

### Full usable

- **n** = 52495
- **class counts** (0/1/2) = 5290 / 43103 / 4102
- **overall accuracy** = 74.96% (0.7496)
- **class 0** precision=0.3984 recall=0.9894 F1=0.5681
- **class 2** precision=0.4412 recall=0.9922 F1=0.6108
- **gated hit rate** = 94.48% (n_gated=290; side0 n=118 hit=93.22%; side2 n=172 hit=95.35%)

### Last 2y

- **n** = 17521
- **class counts** (0/1/2) = 1762 / 14268 / 1491
- **overall accuracy** = 76.81% (0.7681)
- **class 0** precision=0.4186 recall=0.9886 F1=0.5882
- **class 2** precision=0.4785 recall=0.9933 F1=0.6459
- **gated hit rate** = 98.61% (n_gated=72; side0 n=23 hit=100.00%; side2 n=49 hit=97.96%)

## ETH

### Full usable

- **n** = 52495
- **class counts** (0/1/2) = 5017 / 43924 / 3554
- **overall accuracy** = 73.95% (0.7395)
- **class 0** precision=0.3679 recall=0.9886 F1=0.5362
- **class 2** precision=0.4105 recall=0.9941 F1=0.5811
- **gated hit rate** = 90.05% (n_gated=382; side0 n=216 hit=90.74%; side2 n=166 hit=89.16%)

### Last 2y

- **n** = 17521
- **class counts** (0/1/2) = 1532 / 14632 / 1357
- **overall accuracy** = 73.61% (0.7361)
- **class 0** precision=0.3609 recall=0.9869 F1=0.5285
- **class 2** precision=0.4128 recall=0.9926 F1=0.5831
- **gated hit rate** = 94.27% (n_gated=157; side0 n=76 hit=96.05%; side2 n=81 hit=92.59%)

## BNB

### Full usable

- **n** = 52495
- **class counts** (0/1/2) = 5582 / 43505 / 3408
- **overall accuracy** = 70.36% (0.7036)
- **class 0** precision=0.3450 recall=0.9907 F1=0.5118
- **class 2** precision=0.4044 recall=0.9930 F1=0.5748
- **gated hit rate** = 93.33% (n_gated=345; side0 n=202 hit=94.55%; side2 n=143 hit=91.61%)

### Last 2y

- **n** = 17521
- **class counts** (0/1/2) = 1830 / 14402 / 1289
- **overall accuracy** = 69.08% (0.6908)
- **class 0** precision=0.3367 recall=0.9907 F1=0.5026
- **class 2** precision=0.4129 recall=0.9946 F1=0.5835
- **gated hit rate** = 94.53% (n_gated=128; side0 n=62 hit=96.77%; side2 n=66 hit=92.42%)

## SOL

### Full usable

- **n** = 52495
- **class counts** (0/1/2) = 4641 / 43439 / 4415
- **overall accuracy** = 75.69% (0.7569)
- **class 0** precision=0.4000 recall=0.9813 F1=0.5683
- **class 2** precision=0.4300 recall=0.9934 F1=0.6002
- **gated hit rate** = 88.29% (n_gated=316; side0 n=114 hit=93.86%; side2 n=202 hit=85.15%)

### Last 2y

- **n** = 17521
- **class counts** (0/1/2) = 1548 / 14527 / 1446
- **overall accuracy** = 74.49% (0.7449)
- **class 0** precision=0.3789 recall=0.9845 F1=0.5472
- **class 2** precision=0.4257 recall=0.9952 F1=0.5964
- **gated hit rate** = 82.89% (n_gated=76; side0 n=25 hit=88.00%; side2 n=51 hit=80.39%)

## XRP

### Full usable

- **n** = 52495
- **class counts** (0/1/2) = 5343 / 43394 / 3758
- **overall accuracy** = 75.45% (0.7545)
- **class 0** precision=0.4168 recall=0.9822 F1=0.5853
- **class 2** precision=0.4072 recall=0.9899 F1=0.5771
- **gated hit rate** = 98.89% (n_gated=180; side0 n=121 hit=98.35%; side2 n=59 hit=100.00%)

### Last 2y

- **n** = 17521
- **class counts** (0/1/2) = 1609 / 14406 / 1506
- **overall accuracy** = 72.85% (0.7285)
- **class 0** precision=0.3766 recall=0.9938 F1=0.5462
- **class 2** precision=0.4172 recall=0.9940 F1=0.5878
- **gated hit rate** = 98.57% (n_gated=70; side0 n=35 hit=97.14%; side2 n=35 hit=100.00%)

## Notes

- Pooled RF has no symbol ID; symbol differences reflect feature-space transfer only.
- Metrics are in-sample relative to the pooled training set (train used random 80/20 split across all symbols), so full-set accuracy is optimistic vs true OOS.

