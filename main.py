from jetcam.usb_camera import USBCamera
import torchvision.transforms as transforms
from dataset import ImageClassificationDataset

# CAMERA

camera = USBCamera(width=224, height=224, capture_device=0)  # confirm the capture_device number

camera.running = True
print("camera created")

# TASK

TASK = 'lego'

CATEGORIES = ['none', 'axle', 'beam', 'gear', 'peg']

DATASETS = ['A', 'B']

TRANSFORMS = transforms.Compose([
    transforms.ColorJitter(0.2, 0.2, 0.2, 0.2),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

datasets = {} # check if this entire section is even needed
for name in DATASETS:
    datasets[name] = ImageClassificationDataset('../data/classification/' + TASK + '_' + name, CATEGORIES, TRANSFORMS)

print("{} task with {} categories defined".format(TASK, CATEGORIES))

# initialize active dataset
dataset = datasets[DATASETS[0]]

# unobserve all callbacks from camera in case we are running this for second time
camera.unobserve_all()

# MODEL

import torch
import torchvision

device = torch.device('cuda')

# RESNET 18
model = torchvision.models.resnet18(pretrained=True)
model.fc = torch.nn.Linear(512, len(dataset.categories))

model = model.to(device)

model_path = "legosort.pth"

print("model configured")

# LIVE EXECUTION

import threading
import time
from utils import preprocess
import torch.nn.functional as F

state = "live"
score_data = [0] * len(dataset.categories)

def live(state, model, camera): # main function that executes. Stop/pause logic should affect this
    global dataset
    while state == "live":
        image = camera.value
        preprocessed = preprocess(image)
        output = model(preprocessed)
        output = F.softmax(output, dim=1).detach().cpu().numpy().flatten()
        category_index = output.argmax()
        for i, score in enumerate(list(output)):
            score_data[i] = str(round(score,1))
        print(str(score_data) + " Prediction: " + dataset.categories[category_index] + "     ", end="\r")

print("live execution ready")

# EVALUATION

BATCH_SIZE = 8

optimizer = torch.optim.Adam(model.parameters())
# optimizer = torch.optim.SGD(model.parameters(), lr=1e-3, momentum=0.9)


model.load_state_dict(torch.load(model_path))
model.eval()
execute_thread = threading.Thread(target=live, args=(state, model, camera))
execute_thread.start()
print("Model loaded and running")

print("----------------")
print("Wait up to 1 min" , end="\r")
