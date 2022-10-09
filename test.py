import argparse
import numpy as np
import os
import pandas as pd
import scipy.misc
import time
import torch
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.parallel
import torch.optim as optim
import torchvision.models as models
from PIL import Image
from averagemeter import AverageMeter
from models import *
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle
from torch.autograd import Variable
from torch.utils.data import sampler
from torchvision import datasets
from torchvision import transforms
    
# GLOBAL CONSTANTS
INPUT_SIZE = 224
NUM_CLASSES = 185
USE_CUDA = torch.cuda.is_available()
best_prec1 = 0
classes = []

# ARGS Parser
parser = argparse.ArgumentParser(description='PyTorch LeafSnap Training')
parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')
parser.add_argument('--testdata', required = True, type=str, metavar='DATA_FOLDER',
                    help='path to test data')
args = parser.parse_args()

# Test method
def test(test_loader, model, criterion):
    batch_time = AverageMeter()
    losses = AverageMeter()
    top1 = AverageMeter()
    top5 = AverageMeter()
    # switch to evaluate mode
    model.eval()

    end = time.time()
    for i, (input, target) in enumerate(test_loader):
        if USE_CUDA:
            input = input.cuda(non_blocking=True)
            target = target.cuda(non_blocking=True)
        with torch.no_grad(): 
            input_var = torch.autograd.Variable(input)
            target_var = torch.autograd.Variable(target)

        # compute output
        output = model(input_var)
        loss = criterion(output, target_var)

        # measure accuracy and record loss
        prec1, prec5 = accuracy(output.data, target, topk=(1, 5))
        value, predicted = torch.max(output.data, 1)
#        print('\nGroundTruth: ', ' '.join('%5s' % classes[target_var.item()]))
        print('Species: ', ''.join('%5s' % classes[predicted.item()]), 'Confidence: %0.2f%%'%value,)
        losses.update(loss.item(), input.size(0))
        top1.update(prec1.item(), input.size(0))
        top5.update(prec5.item(), input.size(0))

        # measure elapsed time
        batch_time.update(time.time() - end)
        end = time.time()

    return top1.avg

def accuracy(output, target, topk=(1,)):
    """Computes the precision@k for the specified values of k"""
    maxk = max(topk)
    batch_size = target.size(0)

    _, pred = output.topk(maxk, 1, True, True)
    pred = pred.t()
    correct = pred.eq(target.view(1, -1).expand_as(pred))

    res = []
    for k in topk:
        correct_k = correct[:k].view(-1).float().sum(0)
        res.append(correct_k.mul_(100.0 / batch_size))
    return res

#print('\n[INFO] Creating Model')
model = models.resnet18(pretrained=False)
model.fc = nn.Linear(512, 185)

criterion = nn.CrossEntropyLoss()
if USE_CUDA:
    model = torch.nn.DataParallel(model).cuda()
    criterion = criterion.cuda()

if args.resume:
    if os.path.isfile(args.resume):
#        print("=> loading checkpoint '{}'".format(args.resume))
        checkpoint = torch.load(args.resume, map_location = 'cpu')
        args.start_epoch = checkpoint['epoch']
        best_prec1 = checkpoint['best_prec1']
        
        state_dict = checkpoint['state_dict']
        
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        
        for k, v in state_dict.items():
            name = k[7:] # remove `module.`
            new_state_dict[name] = v
        model.load_state_dict(new_state_dict)        
#        print("=> loaded checkpoint '{}' (epoch {})"
#              .format(args.resume, checkpoint['epoch']))
    else:
        print("=> no checkpoint found at '{}'".format(args.resume))

#print('\n[INFO] Reading Training and Testing Dataset')
traindir = os.path.join('dataset', 'train_224')
print(args.testdata)
testdir = args.testdata
normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
data_train = datasets.ImageFolder(traindir)
data_test = datasets.ImageFolder(testdir, transforms.Compose([
            transforms.ToTensor(),
            normalize,
#            Resize(size = (16,16)),
            ]))
classes = data_train.classes

test_loader = torch.utils.data.DataLoader(data_test, batch_size=1, shuffle=False, num_workers=0)

#print('\n[INFO] Testing on Original Test Data Started')
prec1 = test(test_loader, model, criterion)
#print(prec1)

print('\n[DONE]')

