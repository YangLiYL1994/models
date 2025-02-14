# Copyright 2022 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for official.nlp.projects.kernel.attention."""
import itertools

from absl.testing import parameterized
import tensorflow as tf

from official.nlp.modeling.layers import kernel_attention as attention


_FEATURE_TRANSFORM = ['relu', 'elu', 'exp', 'expplus']
_REDRAW = [True, False]
_TRAINING = [True, False]
_IS_SHORT_SEQ = [True, False]
_BEGIN_KERNEL = [0, 512]


class KernelAttentionTest(tf.test.TestCase, parameterized.TestCase):

  @parameterized.parameters(
      itertools.product(_FEATURE_TRANSFORM, [127], _TRAINING, [True, False],
                        _IS_SHORT_SEQ, _BEGIN_KERNEL))
  def test_attention_projection(
      self, feature_transform, num_random_features, training, redraw, is_short,
      begin_kernel):
    num_heads = 12
    key_dim = 64
    seq_length = 1024
    batch_size = 2
    test_layer = attention.KernelAttention(
        num_heads=num_heads,
        key_dim=key_dim,
        feature_transform=feature_transform,
        num_random_features=num_random_features,
        redraw=redraw,
        is_short_seq=is_short,
        begin_kernel=begin_kernel)
    query = tf.random.normal(
        shape=(batch_size, seq_length, key_dim))
    value = query
    encoder_inputs_mask = tf.zeros((batch_size, seq_length), dtype=tf.int32)
    masks = tf.cast(encoder_inputs_mask, dtype=tf.float32)
    output = test_layer(
        query=query,
        value=value,
        attention_mask=masks,
        training=training)
    self.assertEqual(output.shape, [batch_size, seq_length, key_dim])

  @parameterized.parameters(
      itertools.product(_FEATURE_TRANSFORM, [127], _TRAINING, [True, False],
                        [0]))
  def test_windowed_causal_attention_projection(
      self, feature_transform, num_random_features, training, redraw,
      begin_kernel):
    num_heads = 12
    key_dim = 64
    seq_length = 1024
    batch_size = 2
    test_layer = attention.KernelAttention(
        num_heads=num_heads,
        key_dim=key_dim,
        feature_transform=feature_transform,
        num_random_features=num_random_features,
        redraw=redraw,
        is_short_seq=False,
        begin_kernel=begin_kernel,
        use_windowed_causal=True,
        chunk_length=8,
        window_length=3)
    query = tf.random.normal(
        shape=(batch_size, seq_length, key_dim))
    value = query
    encoder_inputs_mask = tf.zeros((batch_size, seq_length), dtype=tf.int32)
    masks = tf.cast(encoder_inputs_mask, dtype=tf.float32)
    output = test_layer(
        query=query,
        value=value,
        attention_mask=masks,
        training=training)
    self.assertEqual(output.shape, [batch_size, seq_length, key_dim])

  @parameterized.parameters(itertools.product(
      _FEATURE_TRANSFORM, [0], _TRAINING, [False],
      _IS_SHORT_SEQ, _BEGIN_KERNEL))
  def test_attention_no_projection(
      self, feature_transform, num_random_features, training, redraw, is_short,
      begin_kernel):
    num_heads = 12
    key_dim = 64
    seq_length = 1024
    batch_size = 2
    test_layer = attention.KernelAttention(
        num_heads=num_heads,
        key_dim=key_dim,
        feature_transform=feature_transform,
        num_random_features=num_random_features,
        redraw=redraw,
        is_short_seq=is_short,
        begin_kernel=begin_kernel)
    query = tf.random.normal(
        shape=(batch_size, seq_length, key_dim))
    value = query
    encoder_inputs_mask = tf.zeros((batch_size, seq_length), dtype=tf.int32)
    masks = tf.cast(encoder_inputs_mask, dtype=tf.float32)
    output = test_layer(
        query=query,
        value=value,
        attention_mask=masks,
        training=training)
    self.assertEqual(output.shape, [batch_size, seq_length, key_dim])

  @parameterized.parameters([128, 512])
  def test_attention_scale_by_length(self, seq_length):
    num_heads = 12
    key_dim = 64
    batch_size = 2
    test_layer = attention.KernelAttention(
        num_heads=num_heads,
        key_dim=key_dim,
        num_random_features=0,
        scale_by_length=True)
    query = tf.random.normal(
        shape=(batch_size, seq_length, key_dim))
    value = query
    encoder_inputs_mask = tf.ones((batch_size, seq_length), dtype=tf.int32)
    masks = tf.cast(encoder_inputs_mask, dtype=tf.float32)
    output_scale_by_length = test_layer(
        query=query, value=value, attention_mask=masks)

    test_layer._scale_by_length = False
    output_no_scale_by_length = test_layer(
        query=query, value=value, attention_mask=masks)
    if seq_length == 512:  # Equals because log(seq_length, base=512) = 1.0
      self.assertAllClose(output_scale_by_length, output_no_scale_by_length)
    else:
      self.assertNotAllClose(output_scale_by_length, output_no_scale_by_length)

  def test_unsupported_feature_transform(self):
    with self.assertRaisesRegex(ValueError, 'Unsupported feature_transform.*'):
      _ = attention.KernelAttention(feature_transform='test')

  def test_redraw_true_no_projection(self):
    with self.assertRaisesRegex(
        ValueError, 'There is nothing to redraw when num_random_features.*'):
      _ = attention.KernelAttention(
          num_heads=2, key_dim=64, feature_transform='elu',
          num_random_features=0, redraw=True)

  def test_config(self):
    num_heads = 12
    key_dim = 64
    test_layer = attention.KernelAttention(
        num_heads=num_heads,
        key_dim=key_dim,
        feature_transform='exp',
        num_random_features=128,
        is_short_seq=True)
    new_layer = attention.KernelAttention.from_config(
        test_layer.get_config())
    # If the serialization was successful, the new config should match the old.
    self.assertAllEqual(test_layer.get_config(), new_layer.get_config())

if __name__ == '__main__':
  tf.test.main()
