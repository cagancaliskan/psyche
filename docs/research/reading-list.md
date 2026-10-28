# Reading list

> Public summary. Detail is withheld until submission under the [disclosure policy](disclosure-policy.md).

These are the classic works behind the question the cognitive-map line, stage 2 of Psyche,
asks. They describe behaviour that suggests animals learn a map of their environment, neural
findings that tie such maps to particular cells, a reinforcement-learning idea used as
background for one comparator, and an analysis that limits what can be said about energy.

The list is short on purpose. It is not a survey of related work, and an entry says nothing
about how the spiking model works. Every DOI below was checked against its Crossref record, and
the book's handle against the repository that holds it, before the entry was listed.

## Behaviour

- Tolman, E. C. (1948). Cognitive maps in rats and men. *Psychological Review*, 55(4),
  189-208. [doi:10.1037/h0061626](https://doi.org/10.1037/h0061626)

  A review of maze experiments with rats, latent learning among them. It holds that learning
  consists in building up, in the nervous system, sets that function like cognitive maps, and not
  in stimulus-response connections, and it closes by turning to human behaviour. It frames the
  question the line asks.

- Tolman, E. C., Ritchie, B. F., and Kalish, D. (1946). Studies in spatial learning. I.
  Orientation and the short-cut. *Journal of Experimental Psychology*, 36(1), 13-24.
  [doi:10.1037/h0053944](https://doi.org/10.1037/h0053944)

  Rats trained to reach a goal by a roundabout route found it blocked and were offered new paths.
  Of 56 rats, 36 percent chose the path pointing directly toward the goal's location, and the
  others were spread over the remaining paths in a chance fashion. The authors concluded that
  rats learn to expect goals in specific locations. It is the classic paradigm behind the
  shortcut test.

- Dusek, J. A., and Eichenbaum, H. (1997). The hippocampus and memory for orderly stimulus
  relations. *Proceedings of the National Academy of Sciences*, 94(13), 7109-7114.
  [doi:10.1073/pnas.94.13.7109](https://doi.org/10.1073/pnas.94.13.7109)

  Rats were trained on four overlapping odour discrimination problems that could be encoded
  separately or as one representation of orderly relations among the odours. Normal rats made
  appropriate transitive inferences about odours not presented together in training. After the
  hippocampus was disconnected from either its cortical or its subcortical pathway, rats still
  learned the separate problems but did not show transitive inference. It is one of the classic
  paradigms behind the transitive-inference test.

## Neural representation

- O'Keefe, J., and Dostrovsky, J. (1971). The hippocampus as a spatial map. Preliminary
  evidence from unit activity in the freely-moving rat. *Brain Research*, 34(1), 171-175.
  [doi:10.1016/0006-8993(71)90358-1](https://doi.org/10.1016/0006-8993%2871%2990358-1)

  A short report, titled as preliminary evidence, of recordings from single units in the
  hippocampus of freely moving rats. Some units fired mainly when the rat was in a particular part
  of its environment. Cells of this kind came to be called place cells.

- O'Keefe, J., and Nadel, L. (1978). *The Hippocampus as a Cognitive Map*. Oxford: Clarendon
  Press. ISBN 0198572069. Full text made available by the authors:
  [hdl:10150/620894](https://hdl.handle.net/10150/620894)

  A book-length argument that the hippocampus is a cognitive map. Its chapters cover spatial
  behaviour, anatomy and physiology, review lesion studies, and extend the theory to humans. It
  takes the term "cognitive map" from Tolman and ties it to the neural findings.

- Hafting, T., Fyhn, M., Molden, S., Moser, M.-B., and Moser, E. I. (2005). Microstructure of
  a spatial map in the entorhinal cortex. *Nature*, 436(7052), 801-806.
  [doi:10.1038/nature03721](https://doi.org/10.1038/nature03721)

  Reports grid cells in the medial entorhinal cortex of rats. Each fires at many locations
  that together form a regular triangular lattice across the environment, and neighbouring
  cells share the lattice's orientation and spacing but not its position.

## Reinforcement-learning background

- Dayan, P. (1993). Improving generalization for temporal difference learning: The successor
  representation. *Neural Computation*, 5(4), 613-624.
  [doi:10.1162/neco.1993.5.4.613](https://doi.org/10.1162/neco.1993.5.4.613)

  Argues that generalisation between states should depend on how similar their successors are,
  shows how temporal-difference learning can learn representations that follow this, the
  successor representation, and illustrates the result on a navigation task. The successor
  representation is one of the comparators listed in the [test battery](test-battery.md).

## Energy accounting

- Dampfhoffer, M., Mesquida, T., Valentian, A., and Anghel, L. (2023). <!-- ledger:allow-claim -->
  Are SNNs really more energy-efficient than ANNs? An in-depth hardware-aware study.
  *IEEE Transactions on Emerging Topics in Computational Intelligence*, 7(3), 731-741.
  [doi:10.1109/TETCI.2022.3214509](https://doi.org/10.1109/TETCI.2022.3214509)

  Compares event-based spiking implementations with efficient digital implementations of
  conventional networks, with memory accesses counted. A spiking network built on the
  integrate-and-fire model can compete with an efficient conventional implementation when its
  spike activity is very sparse, and how sparse depends on the conventional implementation it is
  compared with. So whether spiking networks save energy depends on the hardware and on what is
  counted. This is why the line reports energy only as an analytic estimate and makes no general
  efficiency claim ([claims and scope](claims-and-scope.md)).

## Related pages

- [Overview](README.md)
- [Test battery](test-battery.md): its references list further works that it cites
- [Claims and scope](claims-and-scope.md)
- [Glossary](glossary.md)
