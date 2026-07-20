rm(list=ls())

# NOTE ON COVARIATES: this script was edited by hand at different points in
# the project to produce different residualized phenotype files for different
# purposes (e.g. GWAS vs. PWAS inputs), rather than being re-run unchanged
# each time. The regression formula below (Sex + YearOfBirth + PC1-5 +
# f.batch) reflects only the last-saved state of the script, not necessarily
# the exact covariate set used for every phenotype file this pipeline
# consumes -- e.g. some described covariate sets (BMI for GWAS phenotypes,
# height-weight ratio for PWAS phenotypes) are not present in this version.
# If reproducing a specific published result, confirm which covariate set
# that result actually used rather than assuming this script's current state.

# BASE_DIR should point to the root data directory on your system
# (originally /oak/stanford/groups/euan/projects on the Stanford Sherlock cluster).
# LIB_DIR should point to a custom R library location, if one is needed; leave
# as "." to use the default R library search path.
BASE_DIR <- "."
LIB_DIR  <- "."

if (LIB_DIR == ".") {
  library(ggplot2)
  library(preprocessCore)
  library(matrixStats)
} else {
  library(ggplot2, lib.loc = LIB_DIR)
  library(preprocessCore, lib.loc = LIB_DIR) # Make my own library
  library(matrixStats, lib.loc = LIB_DIR)
}

data=read.table(file.path(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles_HHregressed.csv_phenotypes_trimmed.txt"),header=TRUE)
data[data==-1000]=NA
#data <- subset(data, select = -c(hypertension_status, hematocrit))

#remove any outliers more than 3 st dev away from mean 
d_mean=colMeans(data,na.rm=TRUE)
d_sd=colSds(as.matrix(data),na.rm=TRUE )
upper_bound=d_mean+3*d_sd
lower_bound=d_mean-3*d_sd 
for(col in seq(3,ncol(data)))
{
  cur_upper_bound=upper_bound[col]
  cur_lower_bound=lower_bound[col]
  to_truncate_upper=which(data[,col]>cur_upper_bound)
  data[to_truncate_upper,col]=cur_upper_bound 
  to_truncate_lower=which(data[,col]<cur_lower_bound) 
  data[to_truncate_lower,col]=cur_lower_bound
}
data[data==NA]=-1000
#write.table(data,file=file.path(BASE_DIR, "shriya/T1_mean_merged.pheno"),sep='\t',quote=FALSE,row.names=FALSE,col.names=TRUE)
data[data==-1000]=NA
#get residuals
covar=data.frame(read.table(file.path(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles_HHregressed.csv_covariates_trimmed.txt"),header=TRUE,sep='\t'))
covar[covar==-1000]=NA
covar=covar[order(covar$FID),]
#covar=covar[4:nrow(covar),]
data=data[order(data$FID),]
covar$Sex=factor(covar$Sex)
covar$f.batch=factor(covar$f.batch)
residuals_continuous=matrix(nrow=nrow(data),ncol=ncol(data))
residuals_continuous[,1]=data[,1]
residuals_continuous[,2]=data[,2]
for(col in seq(3,ncol(data)))
{
  covar$Y=data[,col]
  residuals=as.vector(residuals(lm(Y ~ Sex
                                   +YearOfBirth
                                   +PC1
                                   +PC2
                                   +PC3
                                   +PC4
                                   +PC5
                                   #+PC6
                                   #+PC7
                                   #+PC8
                                   #+PC9
                                   #+PC10
                                   +f.batch,data=covar,na.action=na.exclude),na.action=na.exclude))
  residuals_continuous[,col]=residuals
}
residuals_continuous=as.data.frame(residuals_continuous)
names(residuals_continuous)=names(data)

#quantile normalize the residuals 
for(col in seq(3,ncol(residuals_continuous)))
{
  residuals_continuous[,col]=normalize.quantiles(as.matrix(residuals_continuous[,col]))
}
residuals_continuous[residuals_continuous==NA]=-1000
write.table(residuals_continuous,file=file.path(BASE_DIR, "shriya/SHMOLLI-output-unet-myocardium-update2/cleaned_T1_percentiles_HHregressed.no_outliers.residuals.qnorm.txt"),sep='\t',quote=FALSE,row.names=FALSE,col.names=TRUE)

