import unittest
import random
import itertools

import dimod

try:
    import networkx as nx
    _networkx = True
except ImportError:
    _networkx = False

try:
    import numpy as np
    _numpy = True
except ImportError:
    _numpy = False


class TestConvert(unittest.TestCase):
    @unittest.skipUnless(_networkx, "No networkx installed")
    def test_to_networkx_graph(self):
        graph = nx.barbell_graph(7, 6)

        # build a BQM
        model = dimod.BinaryQuadraticModel({v: -.1 for v in graph},
                                           {edge: -.4 for edge in graph.edges},
                                           1.3,
                                           vartype=dimod.SPIN)

        # get the graph
        BQM = dimod.to_networkx_graph(model)

        self.assertEqual(set(graph), set(BQM))
        for u, v in graph.edges:
            self.assertIn(u, BQM[v])

        for v, bias in model.linear.items():
            self.assertEqual(bias, BQM.nodes[v]['bias'])

    def test_to_ising_spin_to_ising(self):
        linear = {0: 7.1, 1: 103}
        quadratic = {(0, 1): .97}
        offset = 0.3
        vartype = dimod.SPIN

        model = dimod.BinaryQuadraticModel(linear, quadratic, offset, vartype)

        h, J, off = dimod.to_ising(model)

        self.assertEqual(off, offset)
        self.assertEqual(linear, h)
        self.assertEqual(quadratic, J)

    def test_to_ising_binary_to_ising(self):
        """binary model's to_ising method"""
        linear = {0: 7.1, 1: 103}
        quadratic = {(0, 1): .97}
        offset = 0.3
        vartype = dimod.BINARY

        model = dimod.BinaryQuadraticModel(linear, quadratic, offset, vartype)

        h, J, off = dimod.to_ising(model)

        for spins in itertools.product((-1, 1), repeat=len(model)):
            spin_sample = dict(zip(range(len(spins)), spins))
            bin_sample = {v: (s + 1) // 2 for v, s in spin_sample.items()}

            # calculate the qubo's energy
            energy = off
            for (u, v), bias in J.items():
                energy += spin_sample[u] * spin_sample[v] * bias
            for v, bias in h.items():
                energy += spin_sample[v] * bias

            # and the energy of the model
            self.assertAlmostEqual(energy, model.energy(bin_sample))

    def test_to_qubo_binary_to_qubo(self):
        """Binary model's to_qubo method"""
        linear = {0: 0, 1: 0}
        quadratic = {(0, 1): 1}
        offset = 0.0
        vartype = dimod.BINARY

        model = dimod.BinaryQuadraticModel(linear, quadratic, offset, vartype)

        Q, off = dimod.to_qubo(model)

        self.assertEqual(off, offset)
        self.assertEqual({(0, 0): 0, (1, 1): 0, (0, 1): 1}, Q)

    def test_to_qubo_spin_to_qubo(self):
        """Spin model's to_qubo method"""
        linear = {0: .5, 1: 1.3}
        quadratic = {(0, 1): -.435}
        offset = 1.2
        vartype = dimod.SPIN

        model = dimod.BinaryQuadraticModel(linear, quadratic, offset, vartype)

        Q, off = dimod.to_qubo(model)

        for spins in itertools.product((-1, 1), repeat=len(model)):
            spin_sample = dict(zip(range(len(spins)), spins))
            bin_sample = {v: (s + 1) // 2 for v, s in spin_sample.items()}

            # calculate the qubo's energy
            energy = off
            for (u, v), bias in Q.items():
                energy += bin_sample[u] * bin_sample[v] * bias

            # and the energy of the model
            self.assertAlmostEqual(energy, model.energy(spin_sample))

    @unittest.skipUnless(_numpy, "numpy is not installed")
    def test_to_numpy_array(self):
        # integer-indexed, binary bqm
        linear = {v: v * .01 for v in range(10)}
        quadratic = {(v, u): u * v * .01 for u, v in itertools.combinations(linear, 2)}
        quadratic[(0, 1)] = quadratic[(1, 0)]
        del quadratic[(1, 0)]
        offset = 1.2
        vartype = dimod.BINARY
        bqm = dimod.BinaryQuadraticModel(linear, quadratic, offset, vartype)

        M = dimod.to_numpy_array(bqm)

        self.assertTrue(np.array_equal(M, np.triu(M)))  # upper triangular

        for (row, col), bias in np.ndenumerate(M):
            if row == col:
                self.assertEqual(bias, linear[row])
            else:
                self.assertTrue((row, col) in quadratic or (col, row) in quadratic)
                self.assertFalse((row, col) in quadratic and (col, row) in quadratic)

                if row > col:
                    self.assertEqual(bias, 0)
                else:
                    if (row, col) in quadratic:
                        self.assertEqual(quadratic[(row, col)], bias)
                    else:
                        self.assertEqual(quadratic[(col, row)], bias)

        #

        # integer-indexed, not contiguous
        bqm = dimod.BinaryQuadraticModel({}, {(0, 3): -1}, 0.0, dimod.BINARY)

        with self.assertRaises(ValueError):
            M = dimod.to_numpy_array(bqm)

        #

        # string-labeled, variable_order provided
        linear = {'a': -1}
        quadratic = {('a', 'c'): 1.2, ('b', 'c'): .3}
        bqm = dimod.BinaryQuadraticModel(linear, quadratic, 0.0, dimod.BINARY)

        with self.assertRaises(ValueError):
            dimod.to_numpy_array(bqm, ['a', 'c'])  # incomplete variable order

        M = dimod.to_numpy_array(bqm, ['a', 'c', 'b'])

        self.assertTrue(np.array_equal(M, [[-1., 1.2, 0.], [0., 0., 0.3], [0., 0., 0.]]))
