class CreateOrders < ActiveRecord::Migration[7.0]
  def change
    create_table :orders do |t|
      t.references :user, null: false, foreign_key: true
      t.decimal :total, precision: 10, scale: 2, null: false
      t.string :status, null: false, default: 'pending'
      t.timestamps
    end
    
    add_index :orders, :user_id
    add_index :orders, :status
  end
end
