class AddOrderFields < ActiveRecord::Migration[7.0]
  def change
    add_column :orders, :shipping_address, :text
    add_column :orders, :notes, :text
  end
end
