import json
from pathlib import Path

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

IA_DIR = BASE_DIR / "ia"

DATASET_DIR = IA_DIR / "dataset"

MODEL_PATH = IA_DIR / "model.keras"

CLASS_NAMES_PATH = IA_DIR / "class_names.json"


# ============================================================
# PARÂMETROS DO TREINAMENTO
# ============================================================

IMG_HEIGHT = 224
IMG_WIDTH = 224

BATCH_SIZE = 16

EPOCHS = 25

VALIDATION_SPLIT = 0.20

SEED = 123


# ============================================================
# VERIFICAR DATASET
# ============================================================

if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"\nDataset não encontrado:\n{DATASET_DIR}\n\n"
        "Crie a pasta ia/dataset e coloque as imagens "
        "dentro das respectivas classes."
    )


# ============================================================
# CARREGAR DATASET
# ============================================================

print("\n" + "=" * 70)
print("AGROIA MOXICO - TREINAMENTO DO MODELO")
print("=" * 70)

print(f"\nDataset:")
print(DATASET_DIR)

print("\nCarregando imagens...\n")


train_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=VALIDATION_SPLIT,
    subset="training",
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode="int",
)


validation_ds = tf.keras.utils.image_dataset_from_directory(
    DATASET_DIR,
    validation_split=VALIDATION_SPLIT,
    subset="validation",
    seed=SEED,
    image_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE,
    label_mode="int",
)


# ============================================================
# NOMES DAS CLASSES
# ============================================================

class_names = train_ds.class_names

print("\nClasses encontradas:")

for index, class_name in enumerate(class_names):
    print(f"{index}: {class_name}")


# ============================================================
# VERIFICAR SE AS 11 CLASSES EXISTEM
# ============================================================

expected_classes = [
    "milho_saudavel",
    "milho_ferrugem",
    "milho_mancha_foliar",
    "feijao_saudavel",
    "feijao_antracnose",
    "mandioca_saudavel",
    "mandioca_mosaico",
    "arroz_saudavel",
    "arroz_mancha_foliar",
    "tomate_saudavel",
    "tomate_requeima",
]


missing_classes = [
    class_name
    for class_name in expected_classes
    if class_name not in class_names
]


if missing_classes:
    raise ValueError(
        "\nAs seguintes classes estão faltando no dataset:\n"
        + "\n".join(f"- {name}" for name in missing_classes)
        + "\n\nVerifique os nomes das pastas."
    )


# ============================================================
# VERIFICAR QUANTIDADE DE CLASSES
# ============================================================

NUM_CLASSES = len(class_names)

if NUM_CLASSES != 11:
    raise ValueError(
        f"\nForam encontradas {NUM_CLASSES} classes, "
        "mas o projeto espera exatamente 11 classes."
    )


# ============================================================
# OTIMIZAÇÃO DO DATASET
# ============================================================

AUTOTUNE = tf.data.AUTOTUNE

train_ds = train_ds.cache().shuffle(1000).prefetch(
    buffer_size=AUTOTUNE
)

validation_ds = validation_ds.cache().prefetch(
    buffer_size=AUTOTUNE
)


# ============================================================
# DATA AUGMENTATION
# ============================================================

data_augmentation = keras.Sequential(
    [
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.10),
        layers.RandomZoom(0.10),
        layers.RandomContrast(0.10),
    ],
    name="data_augmentation",
)


# ============================================================
# MODELO
# ============================================================

model = keras.Sequential(
    [
        layers.Input(
            shape=(IMG_HEIGHT, IMG_WIDTH, 3)
        ),

        # Aumento de dados
        data_augmentation,

        # Normalização
        layers.Rescaling(
            1.0 / 255
        ),

        # Primeira camada convolucional
        layers.Conv2D(
            32,
            3,
            padding="same",
            activation="relu",
        ),

        layers.BatchNormalization(),

        layers.MaxPooling2D(),

        # Segunda camada
        layers.Conv2D(
            64,
            3,
            padding="same",
            activation="relu",
        ),

        layers.BatchNormalization(),

        layers.MaxPooling2D(),

        # Terceira camada
        layers.Conv2D(
            128,
            3,
            padding="same",
            activation="relu",
        ),

        layers.BatchNormalization(),

        layers.MaxPooling2D(),

        # Quarta camada
        layers.Conv2D(
            256,
            3,
            padding="same",
            activation="relu",
        ),

        layers.BatchNormalization(),

        layers.MaxPooling2D(),

        # Regularização
        layers.Dropout(0.30),

        # Classificador
        layers.GlobalAveragePooling2D(),

        layers.Dense(
            256,
            activation="relu",
        ),

        layers.Dropout(0.40),

        # 11 classes
        layers.Dense(
            NUM_CLASSES,
            activation="softmax",
        ),
    ]
)


# ============================================================
# COMPILAR MODELO
# ============================================================

model.compile(
    optimizer=keras.optimizers.Adam(
        learning_rate=0.0001
    ),
    loss="sparse_categorical_crossentropy",
    metrics=[
        "accuracy"
    ],
)


# ============================================================
# MOSTRAR MODELO
# ============================================================

print("\nArquitetura do modelo:\n")

model.summary()


# ============================================================
# CALLBACKS
# ============================================================

callbacks = [

    keras.callbacks.EarlyStopping(
        monitor="val_accuracy",
        patience=6,
        restore_best_weights=True,
        verbose=1,
    ),

    keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=3,
        min_lr=1e-7,
        verbose=1,
    ),

]


# ============================================================
# TREINAMENTO
# ============================================================

print("\n")
print("=" * 70)
print("INICIANDO TREINAMENTO")
print("=" * 70)

history = model.fit(
    train_ds,
    validation_data=validation_ds,
    epochs=EPOCHS,
    callbacks=callbacks,
)


# ============================================================
# AVALIAÇÃO
# ============================================================

print("\n")
print("=" * 70)
print("AVALIANDO MODELO")
print("=" * 70)

loss, accuracy = model.evaluate(
    validation_ds,
    verbose=1,
)


print(
    f"\nAcurácia de validação: "
    f"{accuracy * 100:.2f}%"
)

print(
    f"Loss de validação: "
    f"{loss:.4f}"
)


# ============================================================
# SALVAR MODELO
# ============================================================

print("\nSalvando modelo...")

model.save(MODEL_PATH)

print(
    f"\nModelo salvo em:\n{MODEL_PATH}"
)


# ============================================================
# SALVAR CLASSES
# ============================================================

with open(
    CLASS_NAMES_PATH,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        class_names,
        file,
        ensure_ascii=False,
        indent=4,
    )


print(
    f"\nClasses salvas em:\n{CLASS_NAMES_PATH}"
)


# ============================================================
# FINAL
# ============================================================

print("\n")
print("=" * 70)
print("TREINAMENTO CONCLUÍDO COM SUCESSO")
print("=" * 70)

print("\nArquivos gerados:")

print(f"Modelo:")
print(MODEL_PATH)

print(f"\nClasses:")
print(CLASS_NAMES_PATH)

print("\nAgora o AgroIA Moxico pode utilizar o modelo.")
