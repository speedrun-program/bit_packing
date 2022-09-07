
class BitPackingArray:
    """
    a class which lets you use a byte array as if it was an arbitrarily deeply nested
    array with each index being any number of bits wide
    """
    
    def __init__(self, dimensions, bits_per_index):
        self.bits_per_index = bits_per_index
        self.dimensions = tuple(dimensions) if not isinstance(dimensions, int) else (dimensions,)
        
        if any(d <= 0 for d in self.dimensions):
            raise ValueError("all dimensions must be greater than 0")
        elif bits_per_index <= 0:
            raise ValueError("bits_per_index must be greater than 0")
        elif not dimensions:
            raise ValueError("no dimensions given")
        
        total_bits = bits_per_index
        for d in self.dimensions:
            total_bits *= d
        
        total_bytes = (total_bits // 8) + (total_bits % 8 != 0)
        self._array = bytearray(total_bytes)
    
    
    def _index_generator(self, position):
        for depth, (pos, dimension_length) in enumerate(zip(position, self.dimensions)):
            actual_position = pos if pos >= 0 else dimension_length + pos
            if not 0 <= actual_position < dimension_length:
                raise IndexError(f"attempted to access index {pos} of dimension {depth}, which is length {dimension_length}")
            
            yield actual_position
    
    
    def _get_actual_position(self, position): # returns (start_byte, start_bit)
        if isinstance(position, int):
            position = (position,)
        if (len(position) != len(self.dimensions)):
            raise ValueError(
                f"position argument had {len(position)} dimensions, "
                f"but self.dimensions has {len(self.dimensions)} dimensions"
            )
        
        index_generator = self._index_generator(position)
        which_bit = next(index_generator)
        for i, pos in enumerate(index_generator, 1):
            which_bit = (which_bit * self.dimensions[i]) + pos
        which_bit *= self.bits_per_index
        
        return divmod(which_bit, 8)
    
    
    def zero_bytes(self):
        self._array.__init__(len(self._array))
    
    
    def get(self, position):
        which_byte, byte_start_position = self._get_actual_position(position)
        bits_left_to_read = self.bits_per_index
        current_bit_position = min(8 - byte_start_position, bits_left_to_read)
        
        # reading first byte
        value = (self._array[which_byte] >> byte_start_position) & ((1 << current_bit_position) - 1)
        bits_left_to_read -= current_bit_position
        which_byte += 1
        
        # reading middle byte(s)
        while bits_left_to_read >= 8:
            value += self._array[which_byte] << current_bit_position
            bits_left_to_read -= 8
            current_bit_position += 8
            which_byte += 1
        
        #reading last byte
        if bits_left_to_read > 0:
            value += (self._array[which_byte] & ((1 << bits_left_to_read) - 1)) << current_bit_position
        
        return value
    
    
    def set(self, position, new_value):
        if new_value > ((1 << self.bits_per_index) - 1) or new_value < 0:
            raise ValueError(f"value must be in range(0, {((1 << self.bits_per_index) - 1)})")
        
        which_byte, byte_start_position = self._get_actual_position(position)
        bits_left_to_set = self.bits_per_index
        
        # setting first byte
        bits_left_in_first_byte = min(8 - byte_start_position, bits_left_to_set)
        first_byte_start_bits = self._array[which_byte] & ((1 << byte_start_position) - 1)
        current_value_to_write = new_value & ((1 << bits_left_in_first_byte) - 1)
        self._array[which_byte] >>= byte_start_position + bits_left_in_first_byte
        self._array[which_byte] <<= bits_left_in_first_byte
        self._array[which_byte] += current_value_to_write
        self._array[which_byte] <<= byte_start_position
        self._array[which_byte] += first_byte_start_bits
        new_value >>= bits_left_in_first_byte
        bits_left_to_set -= bits_left_in_first_byte
        which_byte += 1
        
        # setting middle byte(s)
        while bits_left_to_set >= 8:
            current_value_to_write = new_value & 0b11111111
            self._array[which_byte] = new_value
            new_value >>= 8
            bits_left_to_set -= 8
            which_byte += 1
        
        # setting last bit
        if bits_left_to_set > 0:
            self._array[which_byte] >>= bits_left_to_set
            self._array[which_byte] <<= bits_left_to_set
            self._array[which_byte] += new_value
    
    
    def append(self, new_value):
        if len(self.dimensions) > 1:
            raise ValueError("appending only supported on 1-dimensional arrays, len(self.dimensions) must be 1")
        
        # allocating more space if necessary
        total_bits = self.bits_per_index * (self.dimensions[0] + 1)
        total_bytes = (total_bits // 8) + (total_bits % 8 != 0)
        while len(self._array) < total_bytes:
            self._array.append(0)
        
        self.dimensions = ((self.dimensions[0] + 1),)
        self.set(-1, new_value)
