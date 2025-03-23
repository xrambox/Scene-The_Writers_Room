import torch
from transformers import RobertaForSequenceClassification, PreTrainedTokenizerFast

class LabelPredictionModel:
    def __init__(self, model_path):
        # Load the model and tokenizer
        self.tokenizer = PreTrainedTokenizerFast.from_pretrained(model_path)
        self.model = RobertaForSequenceClassification.from_pretrained(model_path)
        # Set up device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        # Label map
        self.label_map = {
            0: 'Scene',
            1: 'Scene description',
            2: 'Character',
            3: 'Dialogue',
            4: 'Dialogue metadata',
            5: 'Metadata',
            6: 'Transition'
        }

    def predict_label(self, description):
        # Tokenize the input description
        encoding = self.tokenizer(
            description,
            max_length=512,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        ).to(self.device)
        
        # Generate prediction
        with torch.no_grad():
            outputs = self.model(**encoding)
            logits = outputs.logits
            predicted_class_id = logits.argmax().item()
        
        # Map the predicted class ID to a label
        return self.label_map[predicted_class_id]
