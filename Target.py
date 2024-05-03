{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 26,
   "id": "53c35fc3",
   "metadata": {},
   "outputs": [],
   "source": [
    "import streamlit as st\n",
    "import databutton as db\n",
    "import openai\n",
    "from langchain.chat_models import ChatOpenAI\n",
    "import os\n",
    "import joblib\n",
    "from langchain.text_splitter import CharacterTextSplitter  \n",
    "import string  \n",
    "import pandas as pd\n",
    "from scipy.sparse import csr_matrix \n",
    "import numpy as np\n",
    "import nltk\n",
    "from nltk.corpus import stopwords\n",
    "from nltk.tokenize import word_tokenize\n",
    "from nltk.stem import WordNetLemmatizer\n",
    "from gensim.models import Word2Vec\n",
    "\n",
    "# Title and header\n",
    "st.title(\"Clinical Trial Eligibilty AI\")\n",
    "\n",
    "# pre-trained classifier model\n",
    "classifier = joblib.load('SVM.pkl')"
   ]
  },
  {
   "source": [
    "def clean_text(text):\n",
    "    # Download necessary NLTK resources if not already available\n",
    "    nltk.download('punkt')  # Download tokenizer\n",
    "    nltk.download('stopwords')  # Download stopwords\n",
    "    nltk.download('wordnet')  # Download WordNet for lemmatization\n",
    "    # Step 1: Remove newline/tab patterns, numbers longer than 3 (optional)\n",
    "    pattern = r\"[\\n\\t]\\d+\"  # Capture newline/tab followed by digits\n",
    "    text = re.sub(pattern, \"\", text)\n",
    "    pattern = r'\\b\\d{4,}\\b'  # Match numbers of length greater than 3\n",
    "    text = re.sub(pattern, '', text)\n",
    "    # Step 2: Remove special characters\n",
    "    pattern = r'[^a-zA-Z0-9\\s\\-_]'  # Match non-alphanumeric, whitespace, hyphens, or underscores\n",
    "    text = re.sub(pattern, '', text)\n",
    "    # Step 3: Convert to lowercase\n",
    "    text = text.lower()\n",
    "    # Step 4: Tokenize\n",
    "    tokens = word_tokenize(text)\n",
    "    # Step 5: Remove stop words\n",
    "    stop_words = set(stopwords.words('english'))\n",
    "    filtered_tokens = [word for word in tokens if word not in stop_words]\n",
    "    # Step 6: Lemmatize\n",
    "    lemmatizer = WordNetLemmatizer()\n",
    "    lemmatized_tokens = [lemmatizer.lemmatize(word) for word in filtered_tokens]\n",
    "    # Step 7: Join tokens back into a string\n",
    "    preprocessed_text = ' '.join(lemmatized_tokens)\n",
    "    return preprocessed_text\n",
    "\n",
    "def tfidf_weighted_average(document, word_embeddings, tfidf_weights, default_embedding=None):\n",
    "    \"\"\"\n",
    "    Calculates the tf-IDF weighted average for a document's word embeddings.\n",
    "\n",
    "    Args:\n",
    "        document (str): The text of the document.\n",
    "        word_embeddings (dict): A dictionary mapping words to their embedding vectors.\n",
    "        tfidf_weights (dict): A dictionary mapping words to their TF-IDF weights.\n",
    "        default_embedding (np.ndarray or None, optional): The default embedding vector to use for OOV words. Defaults to None.\n",
    "\n",
    "    Returns:\n",
    "        np.ndarray: The tf-IDF weighted average vector representation of the document.\n",
    "\n",
    "    Raises:\n",
    "        ValueError: If the number of unique words in word_embeddings doesn't match the number of unique words in the document.\n",
    "    \"\"\"\n",
    "    word_counts = Counter(document.split())\n",
    "    total_words = len(word_counts)  # Count of unique words\n",
    "\n",
    "    if default_embedding is None:\n",
    "        default_embedding = np.zeros_like(next(iter(word_embeddings.values())))  # Use the first embedding vector as the default\n",
    "\n",
    "    vocabulary = set(word_counts.keys())\n",
    "\n",
    "    # Ensure that the vocabulary of word_embeddings matches the vocabulary of the document\n",
    "    if set(word_embeddings.keys()) != vocabulary:\n",
    "        raise ValueError(\"Vocabulary of word_embeddings doesn't match the vocabulary of the document\")\n",
    "\n",
    "    # Calculate weighted sum of word embeddings\n",
    "    weighted_sum = np.zeros_like(default_embedding)\n",
    "    for word, count in word_counts.items():\n",
    "        weighted_sum += tfidf_weights[word] * word_embeddings.get(word, default_embedding)\n",
    "\n",
    "    # Calculate mean of weighted word embeddings\n",
    "    average_embedding = weighted_sum / total_words\n",
    "\n",
    "    return average_embedding\n",
    "\n",
    "\n",
    "from gensim.models import Word2Vec\n",
    "\n",
    "def generate_word_embedding(text):\n",
    "    # Tokenize the text into words\n",
    "    tokenized_text = text.split()\n",
    "    # Initialize and train the Word2Vec model\n",
    "    model = Word2Vec([tokenized_text], min_count=1, vector_size=100)  \n",
    "    # Generate word embeddings for the current text using the trained model\n",
    "    word_embeddings = {word: model.wv[word] for word in tokenized_text}\n",
    "    return word_embeddings\n",
    "\n",
    "def generate_features(preprocessed_text,weighted_embeddings):\n",
    "    tfidf_vectorizer = TfidfVectorizer(max_features=1000) \n",
    "    tfidf_features = tfidf_vectorizer.fit_transform(preprocessed_text).astype(np.float64)\n",
    "    X_weighted_embedding = np.array(weighted_embeddings).astype(np.float64)\n",
    "    X = hstack((X_weighted_embedding, tfidf_features))\n",
    "    return X\n",
    "\n",
    "def decode_condition_array(data_array):\n",
    "    label_cols = ['ABDOMINAL', 'CREATININE', 'MAJOR-DIABETES', 'ADVANCED-CAD']\n",
    "    # Convert array to list and get first row\n",
    "    data_list = data_array.tolist()[0]\n",
    "    # Create a dictionary for mapping (assuming all conditions initially met)\n",
    "    label_mapping = {col: 0 for col in label_cols}\n",
    "\n",
    "    # Decode the list based on mapping\n",
    "    decoded_list = []\n",
    "    for i, value in enumerate(data_list):\n",
    "        if value == 0:\n",
    "            decoded_list.append(label_cols[i])  # Append label if condition met\n",
    "        else:\n",
    "            decoded_list.append(\"Not Met\")\n",
    "\n",
    "    return decoded_list"
   ]
  },
  {
   "source": [
    "def chunk_data(text):\n",
    "    char_text_splitter = CharacterTextSplitter(separator=\"\\n\", chunk_size=4000,\n",
    "                                               chunk_overlap=10, length_function=len)\n",
    "    text_chunks = char_text_splitter.split_text(text)\n",
    "    \n",
    "    # Feature extraction with GPT vectorizer\n",
    "    return text_chunks"
   ]
  },
  {
   "source": [
    "# User input\n",
    "user_input = st.text_input(\"Enter the patient clinical text here:\", \"\")\n",
    "\n",
    "if st.button(\"Classify\"):\n",
    "    if user_input:\n",
    "        cleaned_text = clean_text(user_input)\n",
    "        weight_embeddings=tfidf_weighted_average(cleaned_text, generate_word_embedding(cleaned_text), tfidf_weights_input(cleaned_text), default_embedding=None)\n",
    "        X = generate_features(cleaned_text,weight_embeddings)\n",
    "        st.success(\"Classification Results:\")\n",
    "        predictions = SVM.classifier(X)\n",
    "        predictions_n = predictions.toarray() \n",
    "        decoded_list = decode_condition_array(predictions_n)\n",
    "        for label in decoded_list.unique():\n",
    "                st.write(f\"- {label}\")\n",
    "        else:\n",
    "            st.write(\"No labels predicted.\")\n",
    "    else:\n",
    "        st.warning(\"Please enter some text to classify.\")\n"
   ]
    },
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
