# Regole del Cinquecento (variante siciliana / Marianna)

Questo è il regolamento che il motore di gioco deve applicare. Le regole sono state decise dall'utente il 26/09/2026 (vedi `DECISIONI.md`). Non vanno cambiate senza una sua richiesta esplicita.

## Terminologia

- **Cantare 40**: il primo canto della mano. Si mostrano Re e Cavallo dello stesso seme, si prendono 40 punti e quel seme diventa briscola.
- **Cantare 20**: ogni canto successivo. Si mostrano Re e Cavallo di un altro seme e si prendono 20 punti. La briscola non cambia.
- Non si dice mai "dichiarare un matrimonio". Nel codice si usano nomi come `sing_40`, `sing_20`, `can_sing`.
- **Carte franche**: si gioca senza briscola. La presa la vince la carta più alta del seme giocato per primo, e le carte di altri semi non prendono mai.

## Mazzo e valori

40 carte siciliane in 4 semi (denari, coppe, spade, bastoni).

| Carta | Punti | Forza nella presa |
|---|---|---|
| Asso | 11 | 1ª (la più forte) |
| Tre | 10 | 2ª |
| Re | 4 | 3ª |
| Cavallo | 3 | 4ª |
| Fante | 2 | 5ª |
| 7, 6, 5, 4, 2 | 0 | dalla 6ª alla 10ª, in quest'ordine |

Ogni mano vale 120 punti di carte, più i canti.

## Giocatori

- **1v1**: due giocatori.
- **2v2**: due squadre da due, con i compagni seduti uno di fronte all'altro. Si gioca in senso antiorario, cioè verso destra. I punti di ciascun giocatore vanno alla sua squadra.

## Chi comincia

- Nella **prima mano** il giocatore che gioca per primo si sceglie **a caso**. Il **mazziere** è il giocatore **alla sua sinistra** (deciso il 28/09/2026, D11). Online il mazziere non distribuisce niente: serve solo a sapere chi comincia.
- **Dalla seconda mano in poi** si gira **verso destra**: comincia il giocatore alla destra di chi aveva cominciato la mano prima, e il mazziere è sempre quello alla sinistra di chi comincia (cioè chi aveva cominciato la mano prima). Deciso il 28/09/2026 (D11).

## Tempo per turno

- Ogni giocatore ha **30 secondi** per il suo turno. Allo scadere il server gioca al suo posto la carta scelta così: 1) quella con **meno punti**; 2) a parità, una carta **non di briscola**, perché la briscola serve a vincere le prese; 3) a parità, la **più debole** nella presa (il 2 prima del 4, e così via); 4) se resta ancora una parità (per esempio il 4 di coppe e il 4 di spade, senza briscola tra i due), una delle due **a caso**. La mossa automatica **non canta mai**. Deciso il 28/09/2026 (D12).
- Chi si disconnette ha **60 secondi** per rientrare; poi la partita è persa per abbandono.
- Nel **2v2**, se un giocatore abbandona, **perde tutta la squadra**, ma il **rating scende solo a chi ha abbandonato**. Deciso il 28/09/2026 (D13).

## Svolgimento di una mano

1. Si mescola e si danno **5 carte** a testa. Le carte rimaste formano il mazzo.
2. All'inizio della mano **non c'è briscola**.
3. Al suo turno il giocatore può **cantare** (dalla seconda presa in poi), e poi deve giocare una carta.
4. **Non c'è obbligo di rispondere al seme**: si può giocare qualsiasi carta.
5. Chi vince la presa pesca per primo dal mazzo, poi gli altri in ordine di turno. Chi vince la presa gioca per primo nella presa successiva.
6. **Quando il mazzo finisce non cambia niente**: si continua a giocare le carte in mano con le stesse regole, finché le carte non finiscono.

## Chi vince la presa

- Se c'è una briscola e nella presa è stata giocata almeno una carta di briscola, vince la briscola più forte.
- Altrimenti vince la carta più forte **del seme giocato per primo** (carte franche).

## Canti

- Per cantare bisogna avere in mano **Re e Cavallo dello stesso seme**. Nel 2v2 non si può fare coppia con una carta del compagno.
- Si canta **solo nel proprio turno** e **prima di giocare la carta**.
- **Nella prima presa di ogni mano nessuno canta**, né 40 né 20, nemmeno chi gioca dopo il primo: si canta dalla seconda presa in poi. Deciso il 29/09/2026 (P64).
- Non serve aver già vinto una presa.
- Nello stesso turno si possono cantare **più semi**, e altri ancora nei turni successivi.
- Il primo canto della mano vale **40** e fissa la briscola. I canti successivi valgono **20**.
- Il canto si **mostra** agli altri giocatori, sia il 40 sia il 20.
- Se il Re o il Cavallo di un seme viene giocato, quel seme **non si può più cantare**.
- **A mazzo finito** si può cantare solo finché si hanno **almeno 3 carte in mano**. Con 2 carte il canto non è più possibile, anche se sono proprio Re e Cavallo dello stesso seme.

## Punteggio e fine partita

- A fine mano si sommano i punti delle carte prese e i punti dei canti. **L'ultima presa non dà bonus.**
- Il punteggio si accumula mano dopo mano.
- **Punteggio per vincere**: si sceglie all'inizio della partita tra **150, 300 e 500** (deciso il 27/09/2026). Qui sotto è indicato con N.
- Il raggiungimento degli N punti si controlla **solo a fine mano**, anche se un canto li fa raggiungere prima.
- Vince chi a fine mano **arriva ad almeno N** (N esatti bastano: con 500 esatti si vince una partita a 500).
- Se ci arrivano entrambi, vince chi ha il punteggio più alto. **A parità è pareggio.**

## Punti ancora aperti

Vedi `DA-DECIDERE.md`, sezione "Gioco" (per esempio come si formano le squadre nella coda 2v2: D17).
