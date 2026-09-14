suppressMessages(library(lme4))
d <- read.csv("/tmp/ltfu_glmm_data_cov.csv", stringsAsFactors = TRUE)
d$ageband <- relevel(d$ageband, ref="[30, 40)"); d$hivc <- relevel(d$hivc, ref="neg")
ctrl <- glmerControl(optimizer="bobyqa", calc.derivs=FALSE)
m3 <- glmer(aband ~ ageband + sex_std + alcoholism + drug_use + tobacco_use + diabetes +
            hivc + period + scale(region_dot_cov) + (1|region_id),
            data=d, family=binomial, nAGQ=0, control=ctrl)
s2 <- as.numeric(VarCorr(m3)$region_id[1])
co <- summary(m3)$coefficients["scale(region_dot_cov)",]
cat(sprintf("m3 (+cobertura regional DOT): sigma2=%.4f MOR=%.3f | OR por +1 DP de cobertura: %.3f (%.3f-%.3f)\n",
    s2, exp(1.349*sqrt(s2)), exp(co[1]), exp(co[1]-1.96*co[2]), exp(co[1]+1.96*co[2])))
