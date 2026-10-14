import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# -----------------------------
# Model (must match eval.py)
# -----------------------------
class MNISTModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Flatten(),
            torch.nn.Linear(28 * 28, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, 10),
        )

    def forward(self, x):
        return self.net(x)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Data
    transform = transforms.ToTensor()
    train_set = datasets.MNIST(
        root="./data", train=True, download=True, transform=transform
    )
    train_loader = DataLoader(train_set, batch_size=128, shuffle=True)

    # Model
    model = MNISTModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = torch.nn.CrossEntropyLoss()

    # Train
    model.train()
    for epoch in range(5):  # small + fast
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        print(f"Epoch {epoch+1} done")

    # Save checkpoint
    torch.save(model.state_dict(), "mnist.pth")
    print("Saved mnist.pth")


if __name__ == "__main__":
    main()