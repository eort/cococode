require(lme4)
library(plyr) # tools for splitting, applying and combining data
library(ggplot2) # tools for splitting, applying and combining data
library(sjPlot) # tools for splitting, applying and combining data

datafiles <- dir('~/Desktop/pilot2/code',pattern = 'agg_data.csv',full.names = TRUE,recursive=TRUE)
#datafiles_keep <- datafiles[seq(1, length(datafiles), 2)]
data <- read.csv(datafiles) 

gdata <- ddply(data,.(sub_id,dirCoh), summarize, response = mean(response))
ggdata <- ddply(gdata,.(dirCoh), summarize, response = mean(response))

# pool participants
mylogit <- glm(resp_key ~ dirCoh, data = data, family = "binomial")

#hierarchical
m <- glmer(response ~ dirCoh + (1 + dirCoh  |sub_id) , data = data, family = binomial)


gdata$sub_id <- factor(gdata$sub_id)    

dirCoh <- sort(unique(data$dirCoh))
subs <- sort(unique(data$sub_id))

logit <- function(b,x){
    odds <- exp(b[[1]]+b[[2]]*x)
    return(odds/(1+odds))}

resp_predict <- logit(mylogit$coefficients,dirCoh)
plot(dirCoh,resp_predict,type='l',col='red')
for (i in subs){lines(dirCoh,gdata$response[gdata$sub_id ==i])}




plot_model(m, sort.est = TRUE, transform = NULL, show.intercept = TRUE, show.values = TRUE, value.offset = .3,
             title = "DV: Choice of left (0) versus right (1) option",
             colors = "bw", dot.size = 3, vline.color = "#9933FF", line.size = 1)


# and again for absolute coherence on correct response


data <- data[!is.na(data$correct),]
hgdata <- ddply(data,.(sub_id,cur_coherence,cur_dir), summarize, correct = mean(correct))
gdata <- ddply(data,.(sub_id,cur_coherence), summarize, correct = mean(correct))
ggdata <- ddply(gdata,.(cur_coherence), summarize, correct = mean(correct))

# pool participants
mylogit <- glm(correct ~ cur_coherence, data = data, family = "binomial")

#hierarchical
m <- glmer(correct ~ cur_coherence + (1 + cur_coherence  |sub_id) , data = data, family = binomial)


gdata$sub_id <- factor(gdata$sub_id)    

cur_coherence <- sort(unique(data$cur_coherence))
subs <- sort(unique(data$sub_id))

logit <- function(b,x){
    odds <- exp(b[[1]]+b[[2]]*x)
    return(odds/(1+odds))}

resp_predict <- logit(mylogit$coefficients,cur_coherence)
plot(cur_coherence,resp_predict,type='l',col='red')
for (i in subs){lines(cur_coherence,gdata$response[gdata$sub_id ==i])}




plot_model(m, sort.est = TRUE, transform = NULL, show.intercept = TRUE, show.values = TRUE, value.offset = .3,
             title = "DV: Choice of left (0) versus right (1) option",
             colors = "bw", dot.size = 3, vline.color = "#9933FF", line.size = 1)
