# Independent region effect on LTFU, adjusted for individual case-mix (Evelyn 2026-08-11).
# Data: /tmp/ltfu_glmm_data.csv (built by the python prep in this session; evaluated episodes,
# same filter as the paper). Three nested logistic mixed models, random intercept per region:
#   m0: age only                     -> baseline geographic variation
#   m1: + sex, alcohol, drugs, tobacco, diabetes, HIV, period   (case mix)
#   m2: + DOT (tx_administration_type)                          (programmatic; note caveat --
#       DOT is assigned during treatment, so it is a mediator/indication mix, not pure confounder)
# Report: sigma^2, MOR = exp(1.349*sigma), latent ICC, and fixed-effect ORs.
suppressMessages(library(lme4))
d <- read.csv("/tmp/ltfu_glmm_data.csv", stringsAsFactors = TRUE)
d$ageband <- relevel(d$ageband, ref = "[30, 40)")
d$dot     <- relevel(d$dot, ref = "DOT")
d$hivc    <- relevel(d$hivc, ref = "neg")
ctrl <- glmerControl(optimizer = "bobyqa", calc.derivs = FALSE)

fit <- function(f, lab) {
  m <- glmer(f, data = d, family = binomial, nAGQ = 0, control = ctrl)
  s2 <- as.numeric(VarCorr(m)$region_id[1])
  cat(sprintf("%s: sigma2=%.4f  sigma=%.3f  MOR=%.3f  ICC=%.3f\n",
      lab, s2, sqrt(s2), exp(1.349 * sqrt(s2)), s2 / (s2 + pi^2 / 3)))
  m
}
m0 <- fit(aband ~ ageband + (1 | region_id), "m0 idade")
m1 <- fit(aband ~ ageband + sex_std + alcoholism + drug_use + tobacco_use + diabetes +
                 hivc + period + (1 | region_id), "m1 case-mix")
m2 <- fit(aband ~ ageband + sex_std + alcoholism + drug_use + tobacco_use + diabetes +
                 hivc + period + dot + (1 | region_id), "m2 +DOT")

cat("\nORs ajustados (m2):\n")
co <- summary(m2)$coefficients
or <- exp(co[, 1]); lo <- exp(co[, 1] - 1.96 * co[, 2]); hi <- exp(co[, 1] + 1.96 * co[, 2])
for (i in 2:nrow(co)) cat(sprintf("  %-22s OR %.2f (%.2f-%.2f)\n", rownames(co)[i], or[i], lo[i], hi[i]))

# region BLUPs from the fully adjusted model -> spread and correlation with vulnerability
b <- ranef(m2)$region_id
blup <- data.frame(region_id = rownames(b), u = b[, 1])
write.csv(blup, "/tmp/ltfu_region_blups.csv", row.names = FALSE)
q <- quantile(blup$u, c(.1, .25, .5, .75, .9))
cat(sprintf("\nBLUPs (log-odds): p10..p90 = %.2f..%.2f  -> OR p90/p10 = %.2f\n",
    q[1], q[5], exp(q[5] - q[1])))
